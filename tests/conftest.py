import sys
from unittest.mock import MagicMock

# Patch external dependencies before text_server is imported.
# text_server runs module-level code (MQTT connect, file reads) that
# fails outside the container environment.
sys.modules.setdefault("mqtt", MagicMock())
sys.modules.setdefault("name_validator", MagicMock())
sys.modules.setdefault("lib.twillio_lib", MagicMock())

import builtins
_real_open = builtins.open

def _patched_open(path, *args, **kwargs):
    if "greglights_config.json" in str(path):
        import io
        return io.StringIO('{"host": "localhost", "port": 1883, "notifyAdmin": "", "accounts": [{"id": "primary", "fromPhone": ""}]}')
    return _real_open(path, *args, **kwargs)

builtins.open = _patched_open
