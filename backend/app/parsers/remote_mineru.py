import posixpath
import shlex
import stat
import time
from dataclasses import dataclass
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.parsers.base import BaseParser
from backend.app.parsers.local_mineru import LocalMinerUParserAdapter, LocalMinerURun
from backend.app.schemas.parsed import ParsedDocument
from backend.app.services.settings_service import EffectiveMinerURemoteSettings


@dataclass
class RemoteMinerUStatus:
    available: bool
    host: str | None
    user: str
    command: str
    version: str | None = None
    error: str | None = None


class RemoteMinerUParserAdapter(BaseParser):
    """Run MinerU pipeline on a remote SSH server and normalize downloaded artifacts."""

    def __init__(
        self,
        method: str = "auto",
        lang: str = "ch",
        formula: bool = True,
        table: bool = True,
        remote_settings: EffectiveMinerURemoteSettings | None = None,
    ) -> None:
        settings = get_settings()
        if remote_settings:
            self.host = remote_settings.host
            self.port = remote_settings.port
            self.user = remote_settings.user
            self.password = remote_settings.password
            self.key_path = remote_settings.key_path
            self.remote_work_dir = remote_settings.work_dir.rstrip("/")
            self.local_output_root = remote_settings.output_dir
        else:
            self.host = settings.mineru_remote_host
            self.port = settings.mineru_remote_port
            self.user = settings.mineru_remote_user
            self.password = settings.mineru_remote_password
            self.key_path = settings.mineru_remote_key_path
            self.remote_work_dir = settings.mineru_remote_work_dir.rstrip("/")
            self.local_output_root = settings.mineru_remote_output_dir
        self.command = settings.mineru_cli_command
        self.timeout = settings.mineru_cli_timeout_seconds
        self.method = method
        self.lang = lang
        self.formula = formula
        self.table = table
        self.last_run: LocalMinerURun | None = None

    def parse_pdf(self, pdf_path: Path | str | None = None) -> ParsedDocument:
        if not pdf_path:
            raise ValueError("Remote MinerU parser requires a PDF path.")
        run = self.run_pipeline(Path(pdf_path))
        local_adapter = LocalMinerUParserAdapter(output_dir=run.output_dir)
        raw = local_adapter.load_best_artifact(Path(run.output_dir))
        return local_adapter.normalize_mineru_output(
            raw, source_file=str(pdf_path), output_dir=Path(run.output_dir)
        )

    def check_status(self) -> RemoteMinerUStatus:
        if not self.host:
            return RemoteMinerUStatus(
                available=False,
                host=None,
                user=self.user,
                command=self.command,
                error="MEDRAG_MINERU_REMOTE_HOST is not configured.",
            )
        try:
            ssh = self._connect()
            version_command = f"{shlex.quote(self.command)} --version"
            stdout, stderr, exit_code = self._exec(ssh, version_command, 15)
            ssh.close()
            output = (stdout or stderr).strip()
            return RemoteMinerUStatus(
                available=exit_code == 0,
                host=self.host,
                user=self.user,
                command=self.command,
                version=output or None,
                error=None if exit_code == 0 else output,
            )
        except Exception as exc:
            return RemoteMinerUStatus(
                available=False,
                host=self.host,
                user=self.user,
                command=self.command,
                error=str(exc),
            )

    def run_pipeline(self, input_path: Path) -> LocalMinerURun:
        if not self.host:
            raise RuntimeError("MEDRAG_MINERU_REMOTE_HOST is not configured.")
        started = time.monotonic()
        work_id = f"{input_path.stem}-{int(started)}"
        remote_root = posixpath.join(self.remote_work_dir, work_id)
        remote_input_dir = posixpath.join(remote_root, "input")
        remote_output_dir = posixpath.join(remote_root, "output")
        remote_input_path = posixpath.join(remote_input_dir, input_path.name)
        local_output_dir = self.local_output_root / work_id
        local_output_dir.mkdir(parents=True, exist_ok=True)

        ssh = self._connect()
        sftp = ssh.open_sftp()
        try:
            mkdir_command = (
                f"mkdir -p {shlex.quote(remote_input_dir)} "
                f"{shlex.quote(remote_output_dir)}"
            )
            self._exec_checked(ssh, mkdir_command)
            sftp.put(str(input_path), remote_input_path)
            command = self._pipeline_command(remote_input_path, remote_output_dir)
            stdout, stderr, exit_code = self._exec(ssh, command, self.timeout)
            self._download_tree(sftp, remote_output_dir, local_output_dir)
            artifacts = [str(path) for path in local_output_dir.rglob("*") if path.is_file()]
            self.last_run = LocalMinerURun(
                command=[command],
                output_dir=str(local_output_dir),
                artifacts=artifacts,
                stdout=stdout[-8000:],
                stderr=stderr[-8000:],
                duration_seconds=round(time.monotonic() - started, 2),
            )
            if exit_code != 0:
                raise RuntimeError(
                    "Remote MinerU pipeline failed: "
                    f"{stderr.strip() or stdout.strip() or exit_code}"
                )
            return self.last_run
        finally:
            sftp.close()
            ssh.close()

    def _connect(self):
        try:
            import paramiko
        except ImportError as exc:  # pragma: no cover - depends on optional runtime
            raise RuntimeError("paramiko is required for remote MinerU SSH mode.") from exc
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs = {
            "hostname": self.host,
            "port": self.port,
            "username": self.user,
            "timeout": 15,
            "banner_timeout": 15,
            "auth_timeout": 15,
        }
        if self.key_path:
            connect_kwargs["key_filename"] = str(self.key_path)
        elif self.password:
            connect_kwargs["password"] = self.password
        client.connect(**connect_kwargs)
        return client

    def _pipeline_command(self, remote_input_path: str, remote_output_dir: str) -> str:
        parts = [
            shlex.quote(self.command),
            "-p",
            shlex.quote(remote_input_path),
            "-o",
            shlex.quote(remote_output_dir),
            "-b",
            "pipeline",
            "-m",
            shlex.quote(self.method),
            "-l",
            shlex.quote(self.lang),
            "-f",
            shlex.quote(str(self.formula)),
            "-t",
            shlex.quote(str(self.table)),
        ]
        return " ".join(parts)

    def _exec_checked(self, ssh, command: str) -> None:
        stdout, stderr, exit_code = self._exec(ssh, command, 30)
        if exit_code != 0:
            raise RuntimeError(stderr.strip() or stdout.strip() or command)

    def _exec(self, ssh, command: str, timeout: int) -> tuple[str, str, int]:
        _, stdout_file, stderr_file = ssh.exec_command(command, timeout=timeout)
        stdout = stdout_file.read().decode("utf-8", errors="replace")
        stderr = stderr_file.read().decode("utf-8", errors="replace")
        exit_code = stdout_file.channel.recv_exit_status()
        return stdout, stderr, exit_code

    def _download_tree(self, sftp, remote_dir: str, local_dir: Path) -> None:
        local_dir.mkdir(parents=True, exist_ok=True)
        for item in sftp.listdir_attr(remote_dir):
            remote_path = posixpath.join(remote_dir, item.filename)
            local_path = local_dir / item.filename
            if stat.S_ISDIR(item.st_mode):
                self._download_tree(sftp, remote_path, local_path)
            else:
                sftp.get(remote_path, str(local_path))
