import os
import shlex
import subprocess
import sys
import webbrowser


class ToolLaunchService:
    """Launch local tools with basic Windows-aware process handling."""

    WINDOWS_ELEVATION_REQUIRED = 740
    WINDOWS_DIRECT_EXECUTABLE_EXTENSIONS = {".exe", ".cmd", ".bat", ".py", ".ps1"}
    WINDOWS_SCRIPT_HOST_EXTENSIONS = {".vbs", ".js", ".jse", ".wsf", ".wsh"}
    WINDOWS_JAVA_COMMANDS = {"java", "java.exe", "javaw", "javaw.exe"}
    WINDOWS_PYTHON_COMMANDS = {"python", "python.exe", "py", "py.exe", "pythonw", "pythonw.exe"}

    def _result(
        self,
        success: bool,
        path: str = "",
        working_directory: str = "",
        command_preview: str = "",
        launch_mode: str = "",
        error_message: str = "",
        requires_elevation: bool = False,
    ):
        return {
            "success": bool(success),
            "path": str(path or ""),
            "working_directory": str(working_directory or ""),
            "command_preview": str(command_preview or ""),
            "launch_mode": str(launch_mode or ""),
            "error_message": str(error_message or ""),
            "requires_elevation": bool(requires_elevation),
        }

    @staticmethod
    def _stringify_command(command_argv=None, command_text: str = "") -> str:
        if command_text:
            return str(command_text)
        if not command_argv:
            return ""
        try:
            return subprocess.list2cmdline([str(part) for part in command_argv])
        except Exception:
            return " ".join(str(part) for part in command_argv)

    @staticmethod
    def _split_args(raw_text: str):
        text = (raw_text or "").strip()
        if not text:
            return []
        try:
            return shlex.split(text, posix=False)
        except ValueError:
            return [text]

    @staticmethod
    def _normalize_path(value: str) -> str:
        text = (value or "").strip()
        if not text:
            return ""
        return os.path.abspath(text) if not os.path.isabs(text) else text

    def _resolve_working_directory(self, working_dir: str = "", fallback_path: str = "") -> str:
        explicit_dir = self._normalize_path(working_dir)
        if explicit_dir and os.path.isdir(explicit_dir):
            return explicit_dir

        normalized_fallback = self._normalize_path(fallback_path)
        if normalized_fallback:
            fallback_dir = (
                normalized_fallback
                if os.path.isdir(normalized_fallback)
                else os.path.dirname(normalized_fallback)
            )
            if fallback_dir and os.path.isdir(fallback_dir):
                return fallback_dir

        if explicit_dir:
            return explicit_dir
        if normalized_fallback:
            return (
                normalized_fallback
                if os.path.isdir(normalized_fallback)
                else os.path.dirname(normalized_fallback)
            )
        return os.getcwd()

    def _should_use_terminal_startup_command(self, startup_command: str) -> bool:
        command_text = (startup_command or "").strip()
        if not command_text:
            return False
        if "{path}" in command_text:
            return True

        parsed = self._split_args(command_text)
        if not parsed:
            return False

        first_token = (parsed[0] or "").strip()
        if not first_token:
            return False
        if first_token.startswith("-"):
            return False
        if first_token.startswith("/") and not os.path.isabs(first_token):
            return False
        return True

    def _format_terminal_startup_command(self, startup_command: str, path: str = "") -> str:
        command_text = (startup_command or "").strip()
        if not command_text:
            return ""

        normalized_path = self._normalize_path(path)
        if "{path}" in command_text:
            quoted_path = subprocess.list2cmdline([normalized_path or ""])
            command_text = command_text.replace("{path}", quoted_path)
            return command_text

        parsed = self._split_args(command_text)
        if not parsed:
            return command_text

        first_token = (parsed[0] or "").strip().strip('"')
        if first_token and not os.path.isabs(first_token) and not any(sep in first_token for sep in ("/", "\\")):
            working_dir = normalized_path if os.path.isdir(normalized_path) else os.path.dirname(normalized_path)
            local_candidate = os.path.join(working_dir, first_token) if working_dir else ""
            if local_candidate and os.path.exists(local_candidate):
                parsed[0] = local_candidate
                return subprocess.list2cmdline(parsed)

        return command_text

    @staticmethod
    def _normalize_type_label(tool_data: dict = None) -> str:
        if not isinstance(tool_data, dict):
            return ""
        return str(tool_data.get("type_label", "") or "").strip()

    def _has_explicit_terminal_launch(self, tool_data: dict = None, run_in_terminal: bool = False) -> bool:
        type_label = self._normalize_type_label(tool_data)
        if type_label in {"终端", "终端工具"}:
            return True
        return bool(run_in_terminal)

    def _should_launch_in_terminal(
        self,
        path: str,
        run_in_terminal: bool = False,
        tool_data: dict = None,
        custom_interpreter_path: str = "",
    ) -> bool:
        tool_data = tool_data or {}
        if bool(tool_data.get("is_web_tool", False)):
            return False

        if self._has_explicit_terminal_launch(tool_data=tool_data, run_in_terminal=run_in_terminal):
            return True

        normalized_path = self._normalize_path(path)
        if not normalized_path:
            return False

        if sys.platform.startswith("win"):
            return self._should_auto_run_windows_terminal_target(
                normalized_path,
                custom_interpreter_path=custom_interpreter_path,
            )

        ext = os.path.splitext(normalized_path)[1].lower()
        return ext in (".cmd", ".bat", ".py", ".ps1", ".sh")

    @staticmethod
    def is_windows_cui_exe(path: str) -> bool:
        try:
            if not path.lower().endswith(".exe"):
                return False

            with open(path, "rb") as file:
                file.seek(0x3C, os.SEEK_SET)
                pe_header_offset = int.from_bytes(file.read(4), byteorder="little")

                file.seek(pe_header_offset, os.SEEK_SET)
                pe_signature = file.read(4)
                if pe_signature != b"PE\x00\x00":
                    return False

                file.seek(pe_header_offset + 4, os.SEEK_SET)
                file_header = file.read(20)
                optional_header_size = int.from_bytes(file_header[16:18], byteorder="little")

                file.seek(pe_header_offset + 24, os.SEEK_SET)
                optional_header = file.read(optional_header_size)
                magic = int.from_bytes(optional_header[0:2], byteorder="little")
                if magic == 0x10B:
                    subsystem_offset = 0x5C
                elif magic == 0x20B:
                    subsystem_offset = 0x68
                else:
                    return False

                subsystem = int.from_bytes(
                    optional_header[subsystem_offset:subsystem_offset + 2],
                    byteorder="little",
                )
                return subsystem == 0x3
        except (IOError, OSError, IndexError, ValueError):
            return False

    def _open_directory(self, path: str):
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _shell_execute_windows(
        self,
        target: str,
        parameters: str = "",
        working_dir: str = "",
        operation: str = "open",
    ):
        if not sys.platform.startswith("win"):
            return False

        try:
            import ctypes

            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                operation,
                str(target),
                str(parameters or "") or None,
                str(working_dir or "") or None,
                1,
            )
        except Exception:
            return False

        if result <= 32:
            raise OSError(f"{operation} launch failed with ShellExecuteW result {result}")
        return True

    def _open_file_with_default_app(self, path: str, working_dir: str = ""):
        if sys.platform.startswith("win"):
            actual_working_dir = self._resolve_working_directory(working_dir, path)
            if not self._shell_execute_windows(path, working_dir=actual_working_dir):
                os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _is_windows_elevation_error(self, exc: BaseException) -> bool:
        return (
            sys.platform.startswith("win")
            and isinstance(exc, OSError)
            and getattr(exc, "winerror", None) == self.WINDOWS_ELEVATION_REQUIRED
        )

    def _launch_windows_elevated(self, command_argv, working_dir: str = ""):
        if not sys.platform.startswith("win"):
            return False
        if not command_argv:
            return False

        target = str(command_argv[0])
        arguments = subprocess.list2cmdline([str(part) for part in command_argv[1:]])
        return self._shell_execute_windows(
            target,
            parameters=arguments,
            working_dir=working_dir,
            operation="runas",
        )

    def open_terminal(
        self,
        working_dir: str = None,
        startup_command: str = "",
        path: str = "",
        command_argv=None,
    ):
        actual_working_dir = self._resolve_working_directory(working_dir, path)
        formatted_command = self._format_terminal_startup_command(startup_command, path)

        if sys.platform.startswith("win"):
            creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            if formatted_command:
                subprocess.Popen(
                    ["cmd.exe", "/k", formatted_command],
                    cwd=actual_working_dir,
                    creationflags=creationflags,
                )
                return True

            if command_argv:
                subprocess.Popen(
                    command_argv,
                    cwd=actual_working_dir,
                    creationflags=creationflags,
                )
                return True

            subprocess.Popen(
                ["cmd.exe", "/k", ""],
                cwd=actual_working_dir,
                creationflags=creationflags,
            )
            return True

        if formatted_command:
            shell_command = f'cd {shlex.quote(actual_working_dir)} && {formatted_command}; exec $SHELL'
            subprocess.Popen(
                ["x-terminal-emulator", "-e", "sh", "-lc", shell_command],
                cwd=actual_working_dir,
            )
            return True

        if command_argv:
            subprocess.Popen(command_argv, cwd=actual_working_dir)
            return True

        if sys.platform == "darwin":
            subprocess.Popen(["open", "-a", "Terminal", actual_working_dir], cwd=actual_working_dir)
        else:
            subprocess.Popen(["x-terminal-emulator"], cwd=actual_working_dir)
        return True

    def _should_use_windows_shell_open(
        self,
        _ext: str,
        _raw_arguments: str,
        run_in_terminal: bool,
        custom_interpreter_path: str = "",
    ) -> bool:
        if run_in_terminal:
            return False
        if custom_interpreter_path:
            return False
        return True

    def _build_windows_command_argv(self, executable_path: str, raw_arguments: str):
        args_text = (raw_arguments or "").strip()
        if not args_text:
            return [executable_path]

        if "{path}" in args_text:
            injected = args_text.replace("{path}", f'"{executable_path}"')
            parsed = self._split_args(injected)
            return parsed or [executable_path]

        parsed = self._split_args(args_text)
        if not parsed:
            return [executable_path]

        first_token = (parsed[0] or "").strip().strip('"')
        path_norm = os.path.normcase(os.path.normpath(executable_path))
        first_norm = os.path.normcase(os.path.normpath(first_token)) if first_token else ""
        base_norm = os.path.normcase(os.path.basename(executable_path))

        if first_norm == path_norm or os.path.normcase(os.path.basename(first_norm)) == base_norm:
            return parsed

        return [executable_path, *parsed]

    def _build_windows_jar_command_argv(
        self,
        jar_path: str,
        raw_arguments: str,
        run_in_terminal: bool,
        java_command: str = "",
    ):
        java_launcher = java_command or ("java" if run_in_terminal else "javaw")
        args_text = (raw_arguments or "").strip()
        if not args_text:
            return [java_launcher, "-jar", jar_path]

        replaced_text = args_text.replace("{path}", f'"{jar_path}"')
        parsed = self._split_args(replaced_text)
        if not parsed:
            return [java_launcher, "-jar", jar_path]

        first_token = (parsed[0] or "").strip().strip('"')
        first_base = os.path.basename(first_token).lower()
        jar_norm = os.path.normcase(os.path.normpath(jar_path))
        first_norm = os.path.normcase(os.path.normpath(first_token)) if first_token else ""
        java_norm = os.path.normcase(os.path.normpath(java_launcher))

        if first_norm == java_norm or first_base in self.WINDOWS_JAVA_COMMANDS:
            return parsed

        if first_norm == jar_norm or os.path.normcase(os.path.basename(first_norm)) == os.path.normcase(os.path.basename(jar_path)):
            parsed = parsed[1:]

        return [java_launcher, "-jar", jar_path, *parsed]

    def _build_windows_python_command_argv(
        self,
        script_path: str,
        raw_arguments: str,
        python_command: str = "",
    ):
        python_launcher = python_command or sys.executable
        args_text = (raw_arguments or "").strip()
        if not args_text:
            return [python_launcher, script_path]

        replaced_text = args_text.replace("{path}", f'"{script_path}"')
        parsed = self._split_args(replaced_text)
        if not parsed:
            return [python_launcher, script_path]

        first_token = (parsed[0] or "").strip().strip('"')
        script_norm = os.path.normcase(os.path.normpath(script_path))
        first_norm = os.path.normcase(os.path.normpath(first_token)) if first_token else ""
        python_norm = os.path.normcase(os.path.normpath(python_launcher))

        if first_norm == python_norm or os.path.basename(first_token).lower() in self.WINDOWS_PYTHON_COMMANDS:
            return parsed

        if first_norm == script_norm or os.path.normcase(os.path.basename(first_norm)) == os.path.normcase(os.path.basename(script_path)):
            parsed = parsed[1:]

        return [python_launcher, script_path, *parsed]

    def _build_windows_interpreter_command_argv(
        self,
        path: str,
        raw_arguments: str,
        interpreter_path: str,
        interpreter_type: str,
        run_in_terminal: bool,
    ):
        interpreter_kind = (interpreter_type or "").strip().lower()
        interpreter = (interpreter_path or "").strip()
        if not interpreter:
            return None

        ext = os.path.splitext(path)[1].lower()
        if interpreter_kind == "java" or ext == ".jar":
            return self._build_windows_jar_command_argv(path, raw_arguments, run_in_terminal, interpreter)
        if interpreter_kind == "python" or ext == ".py":
            return self._build_windows_python_command_argv(path, raw_arguments, interpreter)

        extra_args = self._split_args(raw_arguments)
        return [interpreter, path, *extra_args]

    def _build_windows_script_host_argv(self, path: str, raw_arguments: str, run_in_terminal: bool):
        host = "cscript.exe" if run_in_terminal else "wscript.exe"
        extra_args = self._split_args(raw_arguments)
        return [host, path, *extra_args]

    def _build_windows_tool_command_argv(
        self,
        path: str,
        raw_arguments: str,
        run_in_terminal: bool,
        custom_interpreter_path: str = "",
        custom_interpreter_type: str = "",
    ):
        ext = os.path.splitext(path)[1].lower()
        command_argv = self._build_windows_interpreter_command_argv(
            path=path,
            raw_arguments=raw_arguments,
            interpreter_path=custom_interpreter_path,
            interpreter_type=custom_interpreter_type,
            run_in_terminal=run_in_terminal,
        )
        if command_argv is not None:
            return command_argv

        if ext == ".jar":
            return self._build_windows_jar_command_argv(path, raw_arguments, run_in_terminal)
        if ext in self.WINDOWS_SCRIPT_HOST_EXTENSIONS:
            return self._build_windows_script_host_argv(path, raw_arguments, run_in_terminal)
        if ext == ".py":
            return self._build_windows_python_command_argv(path, raw_arguments)
        return self._build_windows_command_argv(path, raw_arguments)

    def _build_windows_terminal_argv(self, path: str, command_argv, ext: str):
        extra_args = command_argv[1:] if len(command_argv) > 1 else []

        if ext in (".cmd", ".bat"):
            return ["cmd.exe", "/k", path, *extra_args]

        if ext == ".py":
            return ["cmd.exe", "/k", *command_argv]

        if ext == ".ps1":
            return ["powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", path, *extra_args]

        return command_argv

    def _should_auto_run_windows_terminal_target(
        self,
        path: str,
        custom_interpreter_path: str = "",
    ) -> bool:
        ext = os.path.splitext(path)[1].lower()
        if custom_interpreter_path:
            return True
        if ext in (".cmd", ".bat", ".py", ".ps1", ".jar"):
            return True
        if ext == ".exe":
            return self.is_windows_cui_exe(path)
        return False

    def open_tool_terminal(
        self,
        path: str = "",
        working_dir: str = None,
        tool_data: dict = None,
        prefer_config_command: bool = True,
    ):
        tool_data = tool_data or {}
        normalized_path = self._normalize_path(path or tool_data.get("path", ""))
        if normalized_path and not os.path.exists(normalized_path):
            raise FileNotFoundError(f"工具路径不存在: {normalized_path}")

        arguments = str(tool_data.get("arguments", "") or "").strip()
        custom_interpreter_path = str(tool_data.get("custom_interpreter_path", "") or "").strip()
        custom_interpreter_type = str(tool_data.get("custom_interpreter_type", "") or "").strip().lower()
        configured_working_dir = (working_dir or "").strip() or str(tool_data.get("working_directory", "") or "").strip()
        actual_working_dir = self._resolve_working_directory(configured_working_dir, normalized_path)

        if not normalized_path:
            return self.open_terminal(working_dir=actual_working_dir)

        if os.path.isdir(normalized_path):
            startup_command = arguments if prefer_config_command else ""
            return self.open_terminal(
                working_dir=actual_working_dir,
                startup_command=startup_command,
                path=normalized_path,
            )

        if sys.platform.startswith("win") and not prefer_config_command:
            arguments = ""

        use_config_command = prefer_config_command and self._should_use_terminal_startup_command(arguments)
        if use_config_command:
            return self.open_terminal(
                working_dir=actual_working_dir,
                startup_command=arguments,
                path=normalized_path,
            )

        if sys.platform.startswith("win"):
            if not self._should_auto_run_windows_terminal_target(
                normalized_path,
                custom_interpreter_path=custom_interpreter_path,
            ):
                return self.open_terminal(
                    working_dir=actual_working_dir,
                    path=normalized_path,
                )

            ext = os.path.splitext(normalized_path)[1].lower()
            command_argv = self._build_windows_tool_command_argv(
                path=normalized_path,
                raw_arguments=arguments,
                run_in_terminal=True,
                custom_interpreter_path=custom_interpreter_path,
                custom_interpreter_type=custom_interpreter_type,
            )
            terminal_argv = self._build_windows_terminal_argv(normalized_path, command_argv, ext)
            return self.open_terminal(working_dir=actual_working_dir, command_argv=terminal_argv)

        if sys.platform == "darwin":
            if arguments:
                return self.open_terminal(
                    working_dir=actual_working_dir,
                    command_argv=["open", "-a", "Terminal", "--args", normalized_path, arguments],
                )
            return self.open_terminal(
                working_dir=actual_working_dir,
                command_argv=["open", "-a", "Terminal", normalized_path],
            )

        split_args = self._split_args(arguments) if arguments else []
        return self.open_terminal(
            working_dir=actual_working_dir,
            command_argv=["x-terminal-emulator", "-e", normalized_path, *split_args],
        )

    def launch_local_tool_with_diagnostics(self, path: str, working_dir: str = None, run_in_terminal: bool = False, tool_data: dict = None):
        if not path:
            raise ValueError("工具路径不能为空")

        path = self._normalize_path(path)
        tool_data = tool_data or {}
        arguments = str(tool_data.get("arguments", "") or "").strip()
        custom_interpreter_path = str(tool_data.get("custom_interpreter_path", "") or "").strip()
        custom_interpreter_type = str(tool_data.get("custom_interpreter_type", "") or "").strip().lower()

        if not os.path.exists(path):
            raise FileNotFoundError(f"工具路径不存在: {path}")

        actual_working_dir = self._resolve_working_directory(working_dir, path)
        explicit_terminal_launch = self._has_explicit_terminal_launch(tool_data=tool_data, run_in_terminal=run_in_terminal)

        if os.path.isdir(path):
            if explicit_terminal_launch:
                command_preview = self._format_terminal_startup_command(arguments, path)
                self.open_tool_terminal(
                    path=path,
                    working_dir=actual_working_dir,
                    tool_data=tool_data,
                    prefer_config_command=True,
                )
                return self._result(
                    True,
                    path=path,
                    working_directory=actual_working_dir,
                    command_preview=command_preview or path,
                    launch_mode="terminal",
                )
            self._open_directory(path)
            return self._result(
                True,
                path=path,
                working_directory=actual_working_dir,
                command_preview=path,
                launch_mode="directory",
            )

        if sys.platform.startswith("win"):
            ext = os.path.splitext(path)[1].lower()
            should_run_in_terminal = self._should_launch_in_terminal(
                path=path,
                run_in_terminal=run_in_terminal,
                tool_data=tool_data,
                custom_interpreter_path=custom_interpreter_path,
            )

            if self._should_use_windows_shell_open(ext, arguments, should_run_in_terminal, custom_interpreter_path):
                self._open_file_with_default_app(path, working_dir=actual_working_dir)
                return self._result(
                    True,
                    path=path,
                    working_directory=actual_working_dir,
                    command_preview=path,
                    launch_mode="shell_open",
                )

            command_argv = self._build_windows_tool_command_argv(
                path=path,
                raw_arguments=arguments,
                run_in_terminal=should_run_in_terminal,
                custom_interpreter_path=custom_interpreter_path,
                custom_interpreter_type=custom_interpreter_type,
            )

            if should_run_in_terminal:
                terminal_argv = None
                if explicit_terminal_launch and self._should_use_terminal_startup_command(arguments):
                    command_preview = self._format_terminal_startup_command(arguments, path)
                    terminal_argv = ["cmd.exe", "/k", f'cd /d "{actual_working_dir}" && {command_preview}']
                else:
                    ext = os.path.splitext(path)[1].lower()
                    terminal_argv = self._build_windows_terminal_argv(path, command_argv, ext)
                    command_preview = self._stringify_command(terminal_argv)
                try:
                    self.open_tool_terminal(
                        path=path,
                        working_dir=actual_working_dir,
                        tool_data=tool_data,
                        prefer_config_command=explicit_terminal_launch,
                    )
                except OSError as exc:
                    if not self._is_windows_elevation_error(exc):
                        raise
                    if not self._launch_windows_elevated(terminal_argv or command_argv, working_dir=actual_working_dir):
                        raise
                    return self._result(
                        True,
                        path=path,
                        working_directory=actual_working_dir,
                        command_preview=command_preview,
                        launch_mode="elevated",
                        requires_elevation=True,
                    )
                return self._result(
                    True,
                    path=path,
                    working_directory=actual_working_dir,
                    command_preview=command_preview,
                    launch_mode="terminal",
                )

            spawn_argv = ["cmd.exe", "/c", *command_argv] if ext in (".cmd", ".bat") else command_argv
            try:
                subprocess.Popen(spawn_argv, cwd=actual_working_dir)
            except OSError as exc:
                if not self._is_windows_elevation_error(exc):
                    raise
                if not self._launch_windows_elevated(spawn_argv, working_dir=actual_working_dir):
                    raise
                return self._result(
                    True,
                    path=path,
                    working_directory=actual_working_dir,
                    command_preview=self._stringify_command(spawn_argv),
                    launch_mode="elevated",
                    requires_elevation=True,
                )
            return self._result(
                True,
                path=path,
                working_directory=actual_working_dir,
                command_preview=self._stringify_command(spawn_argv),
                launch_mode="subprocess",
            )

        if sys.platform == "darwin":
            should_run_in_terminal = self._should_launch_in_terminal(
                path=path,
                run_in_terminal=run_in_terminal,
                tool_data=tool_data,
                custom_interpreter_path=custom_interpreter_path,
            )
            if should_run_in_terminal:
                command_preview = self._format_terminal_startup_command(arguments, path) or path
                self.open_tool_terminal(
                    path=path,
                    working_dir=actual_working_dir,
                    tool_data=tool_data,
                    prefer_config_command=explicit_terminal_launch,
                )
                return self._result(
                    True,
                    path=path,
                    working_directory=actual_working_dir,
                    command_preview=command_preview,
                    launch_mode="terminal",
                )
            subprocess.Popen(["open", path], cwd=actual_working_dir)
            return self._result(
                True,
                path=path,
                working_directory=actual_working_dir,
                command_preview=self._stringify_command(["open", path]),
                launch_mode="subprocess",
            )

        should_run_in_terminal = self._should_launch_in_terminal(
            path=path,
            run_in_terminal=run_in_terminal,
            tool_data=tool_data,
            custom_interpreter_path=custom_interpreter_path,
        )
        if should_run_in_terminal:
            command_preview = self._format_terminal_startup_command(arguments, path)
            if not command_preview:
                split_args = self._split_args(arguments) if arguments else []
                command_preview = self._stringify_command([path, *split_args] if split_args else [path])
            self.open_tool_terminal(
                path=path,
                working_dir=actual_working_dir,
                tool_data=tool_data,
                prefer_config_command=explicit_terminal_launch,
            )
            return self._result(
                True,
                path=path,
                working_directory=actual_working_dir,
                command_preview=command_preview,
                launch_mode="terminal",
            )

        subprocess.Popen([path], cwd=actual_working_dir)
        return self._result(
            True,
            path=path,
            working_directory=actual_working_dir,
            command_preview=self._stringify_command([path]),
            launch_mode="subprocess",
        )

    def launch_local_tool(self, path: str, working_dir: str = None, run_in_terminal: bool = False, tool_data: dict = None):
        return self.launch_local_tool_with_diagnostics(
            path=path,
            working_dir=working_dir,
            run_in_terminal=run_in_terminal,
            tool_data=tool_data,
        )["success"]

    def launch_tool(self, tool_data: dict = None, path: str = "", working_dir: str = None, run_in_terminal: bool = False):
        tool_data = tool_data or {}
        target_path = str(path or tool_data.get("path", "") or "").strip()
        is_web_tool = bool(tool_data.get("is_web_tool", False))

        if is_web_tool or target_path.startswith(("http://", "https://")):
            try:
                webbrowser.open(target_path)
                return self._result(
                    True,
                    path=target_path,
                    command_preview=target_path,
                    launch_mode="web",
                )
            except webbrowser.Error as exc:
                return self._result(
                    False,
                    path=target_path,
                    command_preview=target_path,
                    launch_mode="web",
                    error_message=str(exc),
                )

        try:
            return self.launch_local_tool_with_diagnostics(
                path=target_path,
                working_dir=working_dir,
                run_in_terminal=run_in_terminal,
                tool_data=tool_data,
            )
        except (FileNotFoundError, PermissionError, OSError, ValueError) as exc:
            return self._result(
                False,
                path=target_path,
                working_directory=self._resolve_working_directory(working_dir, target_path) if target_path else "",
                error_message=str(exc),
            )
