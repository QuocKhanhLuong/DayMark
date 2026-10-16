"""Owner-controlled sync tests; synthetic setup only, no remote requests."""
import contextlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from activity_dashboard.export import ExportError
import sync_owner

TOKEN = 'synthetic-sync-owner-token-ONLY-1234567890'
CATEGORIES = ('coding', 'github', 'chatgpt', 'orca', 'reading', 'other')


def payload():
    return {'schemaVersion': 1, 'timeZone': 'Asia/Ho_Chi_Minh', 'days': [
        {'date': '2026-10-15', 'status': 'missing', 'seconds': None},
        {'date': '2026-10-16', 'status': 'partial', 'seconds': {key: 60 if key == 'coding' else 0 for key in CATEGORIES}},
    ]}


class OwnerSyncTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        runtime = self.root / '.runtime'
        runtime.mkdir(mode=0o700)
        (runtime / 'app-secrets.json').write_text(json.dumps({'DAYMARK_SYNC_TOKEN': TOKEN}))
        self.output = io.StringIO()
        for manager in (patch.object(sync_owner, 'ROOT', self.root), contextlib.redirect_stdout(self.output)):
            manager.__enter__()
            self.addCleanup(manager.__exit__, None, None, None)

    def test_noninteractive_execution_never_reads_activity_or_sends(self):
        with patch('sync_owner.sys.stdin.isatty', return_value=False), patch('sync_owner.collect_payload') as collect, patch('sync_owner.send_payload') as send:
            self.assertEqual(sync_owner.main(), 1)
        collect.assert_not_called()
        send.assert_not_called()

    def test_cancellation_does_not_read_private_token_or_send(self):
        (self.root / '.runtime/app-secrets.json').unlink()
        with patch('sync_owner.collect_payload', return_value=payload()), patch('builtins.input', return_value='CANCEL'), patch('sync_owner.send_payload') as send:
            self.assertEqual(sync_owner.run_interactive(), 0)
        send.assert_not_called()
        self.assertIn('Cancelled', self.output.getvalue())
        self.assertFalse((self.root / '.runtime/sync-attempt.json').exists())

    def test_demo_or_offline_export_refusal_never_reaches_confirmation_or_network(self):
        with patch('sync_owner.collect_payload', side_effect=ExportError('PRIVATE ' + TOKEN)), patch('builtins.input') as confirm, patch('sync_owner.send_payload') as send:
            self.assertEqual(sync_owner.run_interactive(), 1)
        confirm.assert_not_called()
        send.assert_not_called()
        self.assertNotIn(TOKEN, self.output.getvalue())

    def test_success_sends_one_snapshot_and_keeps_only_a_private_receipt(self):
        data = payload()
        receipt = {'acceptedDays': 2, 'lastSync': '2026-10-16T15:40:00+00:00'}
        with patch('sync_owner.collect_payload', return_value=data), patch('builtins.input', return_value='SYNC'), patch('sync_owner.send_payload', return_value=receipt) as send:
            self.assertEqual(sync_owner.run_interactive(), 0)
        send.assert_called_once_with(data, 'https://daymark-private.vercel.app', TOKEN)
        path = self.root / '.runtime/sync-receipt.json'
        saved = json.loads(path.read_text())
        self.assertEqual(set(saved), {'origin', 'acceptedDays', 'lastSync', 'observedDays', 'status'})
        self.assertEqual(saved['status'], 'confirmed')
        self.assertEqual(saved['observedDays'], 1)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertNotIn(TOKEN, path.read_text() + self.output.getvalue())
        self.assertNotIn('seconds', saved)

    def test_invalid_token_never_sends_or_leaks_its_value(self):
        bad = TOKEN + '\nPRIVATE'
        (self.root / '.runtime/app-secrets.json').write_text(json.dumps({'DAYMARK_SYNC_TOKEN': bad}))
        with patch('sync_owner.collect_payload', return_value=payload()), patch('builtins.input', return_value='SYNC'), patch('sync_owner.send_payload') as send:
            self.assertEqual(sync_owner.run_interactive(), 1)
        send.assert_not_called()
        self.assertNotIn(TOKEN, self.output.getvalue())

    def test_failure_is_uncertain_without_retry_or_secret_error_output(self):
        with patch('sync_owner.collect_payload', return_value=payload()), patch('builtins.input', return_value='SYNC'), patch('sync_owner.send_payload', side_effect=RuntimeError('PRIVATE ' + TOKEN)) as send:
            self.assertEqual(sync_owner.run_interactive(), 1)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(json.loads((self.root / '.runtime/sync-attempt.json').read_text())['status'], 'uncertain')
        self.assertFalse((self.root / '.runtime/sync-receipt.json').exists())
        self.assertNotIn(TOKEN, self.output.getvalue())
        self.assertIn('No automatic retry', self.output.getvalue())

    def test_entirely_missing_snapshot_never_sends_but_observed_zero_is_valid(self):
        data = payload()
        data['days'] = [data['days'][0]]
        with patch('sync_owner.collect_payload', return_value=data), patch('builtins.input') as confirm, patch('sync_owner.send_payload') as send:
            self.assertEqual(sync_owner.run_interactive(), 1)
        confirm.assert_not_called()
        send.assert_not_called()
        data = payload()
        data['days'][1]['seconds'] = dict.fromkeys(CATEGORIES, 0)
        with patch('sync_owner.collect_payload', return_value=data), patch('builtins.input', return_value='SYNC'), patch('sync_owner.send_payload', return_value={'acceptedDays': 2, 'lastSync': '2026-10-16T15:40:00+00:00'}) as send:
            self.assertEqual(sync_owner.run_interactive(), 0)
        self.assertEqual(send.call_count, 1)
