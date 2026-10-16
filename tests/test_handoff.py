"""Synthetic local handoff fixtures; never read the real runtime directory."""
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from urllib.parse import urlsplit, urlunsplit, parse_qs

spec = importlib.util.spec_from_file_location('handoff', Path(__file__).resolve().parents[1] / 'tools/prepare-vercel-handoff.py')
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = {'DATABASE_URL_UNPOOLED': urlunsplit(('postgresql', 'synthetic_user:synthetic-password-only@ep-synthetic.ap-southeast-1.aws.neon.tech', '/daymark', 'sslmode=require', ''))}
        self.secrets = {'BETTER_AUTH_SECRET': 'synthetic-signing-secret-ONLY-1234567890', 'DAYMARK_SYNC_TOKEN': 'synthetic-write-token-ONLY-1234567890'}
        self.owner = {'ownerId': 'synthetic-owner-only'}
        self.save()

    def save(self):
        for name, value in [('database.json', self.database), ('app-secrets.json', self.secrets), ('owner-id.json', self.owner)]:
            (self.root / name).write_text(json.dumps(value))

    def test_only_five_reviewed_values_with_pooling_and_full_certificate_verification(self):
        values = handoff.values_from(self.root)
        self.assertEqual(set(values), set(handoff.KEYS))
        parsed = urlsplit(values['DATABASE_URL'])
        self.assertTrue(parsed.hostname.startswith('ep-synthetic-pooler.'))
        self.assertEqual(parse_qs(parsed.query)['sslmode'], ['verify-full'])
        self.assertNotIn(self.secrets['DAYMARK_SYNC_TOKEN'], values.values())
        self.assertEqual(len(values['SYNC_TOKEN_SHA256']), 64)
        self.assertEqual(values['OWNER_USER_ID'], self.owner['ownerId'])

    def test_missing_owner_refuses_preparation(self):
        (self.root / 'owner-id.json').unlink()
        with self.assertRaises(FileNotFoundError):
            handoff.values_from(self.root)
        self.assertFalse((self.root / 'vercel-handoff').exists())

    def test_bad_connection_or_multiline_setup_values_are_rejected(self):
        original = self.database['DATABASE_URL_UNPOOLED']
        self.database['DATABASE_URL_UNPOOLED'] = original.replace('.neon.tech', '.example.test')
        self.save()
        with self.assertRaises(ValueError):
            handoff.values_from(self.root)
        self.database['DATABASE_URL_UNPOOLED'] = original
        self.secrets['BETTER_AUTH_SECRET'] += '\nEXTRA=private'
        self.save()
        with self.assertRaises(ValueError):
            handoff.values_from(self.root)

    def test_files_are_private_and_values_are_unquoted_for_manual_entry(self):
        values = handoff.values_from(self.root)
        folder = handoff.write_handoff(self.root, values)
        self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)
        self.assertEqual({path.name for path in folder.iterdir()}, {key + '.txt' for key in handoff.KEYS})
        for key in handoff.KEYS:
            path = folder / (key + '.txt')
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(path.read_text(), values[key])

    def test_symlink_outputs_are_refused(self):
        outside = self.root / 'unrelated.txt'
        outside.write_text('unchanged')
        folder = self.root / 'vercel-handoff'
        folder.mkdir()
        (folder / 'APP_ORIGIN.txt').symlink_to(outside)
        with self.assertRaises(OSError):
            handoff.write_handoff(self.root, handoff.values_from(self.root))
        self.assertEqual(outside.read_text(), 'unchanged')
