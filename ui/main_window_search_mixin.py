import difflib


class MainWindowSearchMixin:
    """MainWindow 搜索逻辑混入。"""

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
            self.refresh_current_view()
            return

        self._show_search_labels()
        base_tools = self._get_search_scope_tools()
        query = query.lower()

        filtered_tools = []
        matched_ids = set()
        for tool in base_tools:
            score = self._score_tool_match(tool, query)
            if score <= 0:
                continue

            tool_copy = dict(tool)
            tool_copy["_search_score"] = score
            filtered_tools.append(tool_copy)
            if tool.get("id") is not None:
                matched_ids.add(tool.get("id"))

        try:
            note_hits = self.notes_manager.search_notes(query)
        except Exception:
            note_hits = []

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

        if len(query) <= 2:
            return score

        score_name = difflib.SequenceMatcher(None, query, name).ratio()
        score_desc = difflib.SequenceMatcher(None, query, description).ratio()
        fuzzy_score = max(score_name, score_desc)

        if fuzzy_score >= 0.85:
            score = max(score, 64)
        elif fuzzy_score >= 0.72:
            score = max(score, 52)
        elif fuzzy_score >= 0.60:
            score = max(score, 38)

        return score

    def _get_search_scope_tools(self):
        """获取全局搜索范围内的工具列表。"""
        return self.data_manager.load_tools()

    def _get_base_tool_list_for_current_view(self):
        """获取当前视图基础工具列表。"""
        if self.is_in_favorites:
            return self.data_manager.get_favorite_tools()

        current_category = self.category_view.current_category
        current_subcategory = self.subcategory_view.current_subcategory

        if current_category and current_subcategory:
            return self.data_manager.get_tools_by_category(current_category, current_subcategory)
        if current_category:
            return self.data_manager.get_tools_by_category(current_category)

        return []
