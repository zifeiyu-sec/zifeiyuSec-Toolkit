import difflib
import re


_SEARCH_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


class MainWindowSearchMixin:
    """MainWindow 搜索逻辑混入。"""

    def clear_active_search(self, restore_view=True):
        """Clear the search box without triggering an intermediate refresh."""
        timer = getattr(self, "search_debounce_timer", None)
        if timer is not None:
            timer.stop()
        self._pending_search_text = ""

        search_input = getattr(self, "search_input", None)
        if search_input is None:
            return False

        had_search = bool((search_input.text() or "").strip())
        if had_search:
            search_input.blockSignals(True)
            search_input.clear()
            search_input.blockSignals(False)
            if restore_view:
                self._restore_view_mode_after_search()
            else:
                self._view_mode_before_search = None
        return had_search

    def _restore_view_mode_after_search(self):
        previous_mode = getattr(self, "_view_mode_before_search", None)
        if previous_mode:
            self.current_view_mode = previous_mode
        self._view_mode_before_search = None

    def schedule_search(self, text):
        """对搜索输入做防抖，避免每个按键都触发完整搜索。"""
        pending_text = text if text is not None else getattr(self, "search_input", None).text()
        self._pending_search_text = pending_text or ""

        timer = getattr(self, "search_debounce_timer", None)
        if timer is None:
            self.on_search(self._pending_search_text)
            return

        if not (self._pending_search_text or "").strip():
            timer.stop()
            self.on_search("")
            return

        timer.start(getattr(self, "search_debounce_interval_ms", 200))

    def _execute_pending_search(self):
        """执行已防抖的搜索请求。"""
        self.on_search(getattr(self, "_pending_search_text", ""))

    def has_active_search(self):
        """当前是否存在有效搜索关键字。"""
        search_input = getattr(self, "search_input", None)
        if search_input is None:
            return False
        return bool((search_input.text() or "").strip())

    def _show_search_labels(self):
        self.category_info_label.setText("搜索结果")
        self.view_mode_label.setText("视图: 全局搜索")

    def on_search(self, text):
        """处理搜索请求。"""
        query = (text or "").strip()
        if not query:
            self._restore_view_mode_after_search()
            self.refresh_current_view()
            return

        if getattr(self, "current_view_mode", "") != "search":
            self._view_mode_before_search = getattr(self, "current_view_mode", "category")
        self.is_in_favorites = False
        self.current_view_mode = "search"
        self._apply_view_state_layout()
        self._show_search_labels()
        search_entries = self._get_tool_search_index()
        base_tools = [entry["tool"] for entry in search_entries]
        query = query.lower()

        filtered_tools = []
        matched_ids = set()
        for entry in search_entries:
            tool = entry["tool"]
            score = self._score_tool_match_text(
                entry["name"],
                entry["description"],
                query,
                entry.get("fuzzy_candidates"),
            )
            if score <= 0:
                continue

            tool_copy = dict(tool)
            tool_copy["_search_score"] = score
            filtered_tools.append(tool_copy)
            if tool.get("id") is not None:
                matched_ids.add(tool.get("id"))

        note_hits = self._search_notes_cached(query)

        note_hits_by_key = {
            self.notes_manager.get_note_key(hit.get("tool_id"), hit.get("tool_name", "")): hit
            for hit in note_hits
            if hit.get("tool_id") is not None or hit.get("tool_name")
        }

        for tool in filtered_tools:
            note_hit = note_hits_by_key.get(self.notes_manager.get_note_key(tool.get("id"), tool.get("name", "")))
            if not note_hit:
                continue
            excerpt = note_hit.get("excerpt") or note_hit.get("summary") or tool.get("description", "")
            tool["_display_description"] = f"笔记命中：{excerpt}"
            tool["_search_score"] = tool.get("_search_score", 0) + 12
            if tool.get("id") is not None:
                matched_ids.add(tool.get("id"))

        for tool in base_tools:
            tool_key = self.notes_manager.get_note_key(tool.get("id"), tool.get("name", ""))
            tool_id = tool.get("id")
            note_hit = note_hits_by_key.get(tool_key)
            if not note_hit or tool_id in matched_ids:
                continue

            tool_copy = dict(tool)
            excerpt = note_hit.get("excerpt") or note_hit.get("summary") or tool.get("description", "")
            tool_copy["_display_description"] = f"笔记命中：{excerpt}"
            tool_copy["_search_score"] = 58
            filtered_tools.append(tool_copy)
            if tool_id is not None:
                matched_ids.add(tool_id)

        filtered_tools.sort(
            key=lambda tool: (
                -int(tool.get("_search_score", 0) or 0),
                (tool.get("name") or "").strip().lower(),
                tool.get("id") or 0,
            )
        )
        for tool in filtered_tools:
            tool.pop("_search_score", None)

        self._display_tools(filtered_tools)
        self.refresh_tool_count()

    def _score_tool_match(self, tool, query):
        name = (tool.get("name") or "").lower()
        description = (tool.get("description") or "").lower()
        return self._score_tool_match_text(name, description, query)

    def _score_tool_match_text(self, name, description, query, fuzzy_candidates=None):
        score = 0
        if not query:
            return score

        if name == query:
            score = max(score, 120)
        elif name.startswith(query):
            score = max(score, 104)
        elif query in name:
            score = max(score, 92)

        if query in description:
            score = max(score, 68)

        if score or len(query) <= 2:
            return score

        fuzzy_score = self._score_fuzzy_candidate_tokens(name, description, query, fuzzy_candidates)

        if fuzzy_score >= 0.85:
            score = max(score, 64)
        elif fuzzy_score >= 0.72:
            score = max(score, 52)
        elif fuzzy_score >= 0.60:
            score = max(score, 38)

        return score

    def _build_search_fuzzy_candidates(self, name, description):
        candidates = [name]
        candidates.extend(_SEARCH_TOKEN_RE.findall(name))
        candidates.extend(_SEARCH_TOKEN_RE.findall(description)[:16])

        seen = set()
        result = []
        for candidate in candidates:
            candidate = str(candidate or "").strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            result.append(candidate)
        return tuple(result)

    def _score_fuzzy_candidate_tokens(self, name, description, query, fuzzy_candidates=None):
        query_len = len(query)
        candidates = fuzzy_candidates
        if candidates is None:
            candidates = self._build_search_fuzzy_candidates(name, description)

        best_score = 0.0
        for candidate in candidates:
            candidate = str(candidate or "").strip()
            if not candidate:
                continue

            candidate_len = len(candidate)
            if candidate_len <= 1:
                continue
            if candidate_len > max(48, query_len * 4) and query_len < 12:
                continue
            if abs(candidate_len - query_len) > max(10, query_len * 2):
                continue

            ratio = difflib.SequenceMatcher(None, query, candidate).ratio()
            if ratio > best_score:
                best_score = ratio
                if best_score >= 0.95:
                    break
        return best_score

    def _build_tool_search_index(self, tools=None):
        tools = list(self._get_search_scope_tools() if tools is None else tools)
        signature = tuple(
            (
                tool.get("id"),
                tool.get("name") or "",
                tool.get("description") or "",
            )
            for tool in tools
            if isinstance(tool, dict)
        )
        self._tool_search_index_signature = signature
        self._tool_search_index = [
            {
                "tool": tool,
                "name": (tool.get("name") or "").lower(),
                "description": (tool.get("description") or "").lower(),
                "fuzzy_candidates": self._build_search_fuzzy_candidates(
                    (tool.get("name") or "").lower(),
                    (tool.get("description") or "").lower(),
                ),
            }
            for tool in tools
            if isinstance(tool, dict)
        ]
        return self._tool_search_index

    def _get_tool_search_index(self):
        tools = self._get_search_scope_tools()
        signature = tuple(
            (
                tool.get("id"),
                tool.get("name") or "",
                tool.get("description") or "",
            )
            for tool in tools
            if isinstance(tool, dict)
        )
        if (
            getattr(self, "_tool_search_index", None) is None
            or getattr(self, "_tool_search_index_signature", None) != signature
        ):
            return self._build_tool_search_index(tools)
        return self._tool_search_index

    def invalidate_search_index(self):
        self._tool_search_index = None
        self._tool_search_index_signature = None
        self._note_search_cache = {}

    def _search_notes_cached(self, query):
        cache = getattr(self, "_note_search_cache", None)
        if cache is None:
            cache = {}
            self._note_search_cache = cache

        if query in cache:
            return cache[query]

        try:
            note_hits = self.notes_manager.search_notes(query)
        except Exception:
            note_hits = []

        if len(cache) > 64:
            cache.clear()
        cache[query] = note_hits
        return note_hits

    def _get_search_scope_tools(self):
        """获取全局搜索范围内的工具列表。"""
        return self.data_manager.load_tools()

    def _get_base_tool_list_for_current_view(self):
        """获取当前视图基础工具列表。"""
        if self.is_in_favorites:
            return self.data_manager.get_favorite_tools()

        current_category = self.category_view.current_category or getattr(self, "current_category", None)
        current_subcategory = self.subcategory_view.current_subcategory

        if current_category and current_subcategory:
            return self.data_manager.get_tools_by_category(current_category, current_subcategory)
        if current_category:
            return self.data_manager.get_tools_by_category(current_category)

        return []
