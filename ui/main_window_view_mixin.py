class MainWindowViewMixin:
    """MainWindow 的首页工作台入口逻辑。"""

    def on_show_favorites(self):
        """顶部“收藏”入口回到含收藏区的首页工作台。"""
        self.show_dashboard()
