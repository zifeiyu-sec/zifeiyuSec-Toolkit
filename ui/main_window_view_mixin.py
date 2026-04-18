from PyQt5.QtCore import Qt

from core.logger import logger


class MainWindowViewMixin:
    """MainWindow 的收藏页逻辑。"""

    def on_show_favorites(self):
        """显示收藏页面或从收藏页面返回"""
        if self.is_in_favorites:
            # 当前在收藏页面，点击返回
            self.is_in_favorites = False
            self._apply_view_state_layout()
            previous_state = self._view_state_before_favorites or {}
            self._view_state_before_favorites = None

            # 返回后始终回到分类视图
            self.current_view_mode = "category"

            restored_category_view = False
            previous_category = previous_state.get('category_id')
            previous_subcategory = previous_state.get('subcategory_id')
            is_startup_entry = bool(previous_state.get('is_startup_entry'))

            # 若之前在分类视图，尝试恢复选中的分类/子分类
            if self.current_view_mode == "category" and previous_category:
                try:
                    self.category_view.refresh()
                    if self.category_view.select_category(previous_category):
                        restored_category_view = True
                        if previous_subcategory is not None:
                            self.subcategory_view.load_subcategories(previous_category)
                            if not self.subcategory_view.select_subcategory(previous_subcategory):
                                self.on_category_selected(previous_category)
                except Exception as e:
                    logger.warning("恢复分类视图失败: %s", str(e))
                    restored_category_view = False

            # 若无法恢复分类视图，则按当前模式刷新
            if not restored_category_view:
                # 首次启动后第一次从收藏返回：没有历史分类时自动选中第一个一级分类
                if is_startup_entry and not previous_category:
                    try:
                        first_item = self.category_view.category_list.item(0)
                        if first_item is not None:
                            data = first_item.data(Qt.UserRole) or {}
                            first_category_id = data.get('id')
                            if first_category_id:
                                self.current_view_mode = "category"
                                self.category_view.select_category(first_category_id)
                                restored_category_view = True
                    except Exception as e:
                        logger.warning("首次返回收藏时恢复默认分类失败: %s", str(e))

            if not restored_category_view:
                self.refresh_current_view()
            elif self.has_active_search():
                self.on_search(self.search_input.text())
        else:
            # 当前不在收藏页面，点击进入收藏页面
            self._view_state_before_favorites = {
                "category_id": getattr(self.category_view, "current_category", None),
                "subcategory_id": getattr(self.subcategory_view, "current_subcategory", None),
                "is_startup_entry": bool(self._is_startup_favorites_entry),
            }
            self.is_in_favorites = True
            self._apply_view_state_layout()
            if self.has_active_search():
                self.on_search(self.search_input.text())
                return
            self.category_info_label.setText("我的收藏")
            self.view_mode_label.setText("视图: 收藏")
            favorites = self.data_manager.get_favorite_tools()
            self._display_tools(favorites)
            self.refresh_tool_count()
