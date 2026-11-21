import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'services/velocity/launch.py'
        if path.exists():
            spec = importlib.util.spec_from_file_location('launch', path)
            cls.launch = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.launch)
        else:
            cls.launch = None

    def test_configurator_exists(self):
        self.assertIsNotNone(self.launch, 'startup configurator must exist')

    def test_secret_typo_keeps_stored_secret(self):
        if self.launch is None:
            self.fail('startup configurator missing')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'forwarding.secret'
            good = 'a' * 64
            self.assertEqual(self.launch.secret(p, good), good)
            self.assertEqual(self.launch.secret(p, 'bad\nvalue'), good)
            self.assertEqual(p.read_text(), good)

    def test_missing_secret_fails_closed_with_persistent_random_value(self):
        if self.launch is None:
            self.fail('startup configurator missing')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'forwarding.secret'
            first = self.launch.secret(p, '')
            self.assertGreaterEqual(len(first), 32)
            self.assertEqual(first, self.launch.secret(p, ''))
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)

    def test_invalid_numeric_input_falls_back(self):
        if self.launch is None:
            self.fail('startup configurator missing')
        self.assertEqual(self.launch.number('port', 'invalid', 8080, 1024, 65535), 8080)
        self.assertEqual(self.launch.number('heap', '-1', 2048, 512, 32768), 2048)

    def test_eula_requires_explicit_true(self):
        if self.launch is None:
            self.fail('startup configurator missing')
        for value in ['', 'false', 'yes', '1', 'tru']:
            self.assertFalse(self.launch.accepted(value))
        self.assertTrue(self.launch.accepted('TRUE'))

    def test_proxy_enforces_online_modern_forwarding_and_private_backend(self):
        if self.launch is None:
            self.fail('startup configurator missing')
        import tomllib
        with tempfile.TemporaryDirectory() as d:
            self.launch.proxy_config(Path(d), {'BACKEND_HOST': 'lobby.railway.internal', 'FORWARDING_SECRET': 'a'*64})
            config = tomllib.loads((Path(d) / 'velocity.toml').read_text())
            self.assertTrue(config['online-mode'])
            self.assertEqual(config['player-info-forwarding-mode'], 'modern')
            self.assertEqual(config['servers']['lobby'], 'lobby.railway.internal:25565')
            self.assertEqual(config['bind'], '[::]:25565')
            self.assertEqual(config['forced-hosts'], {})

    def test_paper_enforces_modern_forwarding_without_granting_accounts(self):
        if self.launch is None:
            self.fail('startup configurator missing')
        import yaml
        with tempfile.TemporaryDirectory() as d:
            data = Path(d)
            (data / 'server.properties').write_text('online-mode=true\nenable-rcon=true\n')
            self.launch.paper_config(data, {'FORWARDING_SECRET': 'a'*64, 'WHITELIST_ENABLED': 'typo', 'MOTD': 'Hello\nmalicious=true'})
            cfg = yaml.safe_load((data / 'config/paper-global.yml').read_text())
            self.assertEqual(cfg['proxies']['velocity'], {'enabled': True, 'online-mode': True, 'secret': 'a'*64})
            properties = (data / 'server.properties').read_text()
            self.assertIn('online-mode=false', properties)
            self.assertIn('enable-rcon=false', properties)
            self.assertIn('white-list=true', properties)
            self.assertNotIn('\nmalicious=true', properties)
            self.assertIn('motd=Hellomalicious=true', properties)
            self.assertFalse((data / 'ops.json').exists())
            self.assertFalse((data / 'whitelist.json').exists())

if __name__ == '__main__':
    unittest.main()
