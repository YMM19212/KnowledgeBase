import logging


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def mask_ip(ip: str | None) -> str:
    if not ip:
        return "unknown"
    if ":" in ip:
        return ip
    parts = ip.split(".")
    if len(parts) != 4:
        return ip
    return ".".join(parts[:2] + ["*", "*"])
