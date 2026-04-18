from core.logger import logger


class MainWindowNavigationMixin:
    """MainWindow 的分类导航与当前视图刷新逻辑。"""

    def _resolve_category_display_names(self, category_id, subcategory_id=None):
        categories = self.data_manager.load_categories()
        category_name = "所有工具"
        subcategory_name = ""

        for category in categories:
            if not isinstance(category, dict) or category.get("id") != category_id:
                continue

            category_name = category.get("name", "未知分类")
            if subcategory_id is not None:
                for subcategory in category.get("subcategories", []) or []:
                    if isinstance(subcategory, dict) and subcategory.get("id") == subcategory_id:
                        subcategory_name = subcategory.get("name", "未知子分类")
                        break
            break

        return category_name, subcategory_name

    def _show_browse_labels(self, category_name, subcategory_name=""):
        suffix = f" - {subcategory_name}" if subcategory_name else ""
        self.category_info_label.setText(f"{category_name}{suffix}")
        self.view_mode_label.setText("视图: 分类")

    def _show_empty_browse_state(self):
        self.category_info_label.setText("请选择分类")
        self.view_mode_label.setText("视图: 分类")
        self._display_tools(self._get_base_tool_list_for_current_view())
        self.refresh_tool_count()

    def handle_category_selected(self, category_id):
        """处理一级分类选择。"""
        self.current_category = category_id
        self.current_view_mode = "category"
        self._apply_view_state_layout()
        self.subcategory_view.load_subcategories(category_id)

        if self.has_active_search():
            self.on_search(self.search_input.text())
            return

        category_name, _ = self._resolve_category_display_names(category_id)
        self._show_browse_labels(category_name)
        self._display_tools(self.data_manager.get_tools_by_category(category_id))
        self.refresh_tool_count()

    def handle_subcategory_selected(self, category_id, subcategory_id):
        """处理二级分类选择。"""
        self.current_category = category_id
        self.current_view_mode = "category"
        self._apply_view_state_layout()

        if self.has_active_search():
            self.on_search(self.search_input.text())
            return

        category_name, subcategory_name = self._resolve_category_display_names(category_id, subcategory_id)
        self._show_browse_labels(category_name, subcategory_name)
        self._display_tools(self.data_manager.get_tools_by_category(category_id, subcategory_id))
        self.refresh_tool_count()

    def handle_refresh_current_view(self):
        """按当前状态刷新内容，不改变当前页面模式。"""
        if self.has_active_search():
            self._apply_view_state_layout()
            self.on_search(self.search_input.text())
            return

        self._apply_view_state_layout()

        if self.is_in_favorites:
            favorites = self.data_manager.get_favorite_tools()
            self.category_info_label.setText("我的收藏")
            self.view_mode_label.setText("视图: 收藏")
            self._display_tools(favorites)
            self.refresh_tool_count()
            return

        current_category = getattr(self.category_view, "current_category", None)
        current_subcategory = getattr(self.subcategory_view, "current_subcategory", None)

        if current_subcategory and self.current_view_mode == "category":
            self.handle_subcategory_selected(current_category, current_subcategory)
            return

        if current_category and self.current_view_mode == "category":
            self.handle_category_selected(current_category)
            return

        self._show_empty_browse_state()

    def handle_refresh_all(self):
        """刷新分类、子分类和当前列表。"""
        self._apply_view_state_layout()
        current_category = getattr(self.category_view, "current_category", None)
        if current_category:
            try:
                self.subcategory_view.load_subcategories(current_category)
            except Exception as error:
                logger.warning("刷新子分类视图失败: %s", error)
        self.handle_refresh_current_view()
