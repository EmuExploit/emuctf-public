"""Player submission routes. References never authorize reads."""

import json
import secrets
import shutil
import time
from contextlib import closing
from datetime import datetime, timezone

from flask import abort, current_app, render_template, request, session

from common.upload_tokens import owner_for_session
from support import config
from support.admission import submission_capacity
from support.auth import csrf_valid
from support.mail_screening import screen_email
from support.models import apply_automatic_rejection, player_result, queue_summary
from support.notifications import notify_queue
from support.submission import (
    UploadTooLarge,
    build_message,
    screen_attachments,
    store_attachments,
    validate_submission,
)
from support.upload_access import token_owner


def submission_owner():
    if current_app.config.get('UPLOAD_SITE_ADDRESS'):
        return token_owner()
    # Same-origin development mode retains session + CSRF authorization.
    if not session.get('platform_access') or not csrf_valid('csrf'):
        abort(403)
    return owner_for_session(session['csrf'])


def register_public_routes(app, mailbox):
    @app.get('/malware/availability')
    def support_availability():
        owner = submission_owner()
        # No references or attempts are exposed, and polling reserves no slot.
        with closing(mailbox.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            capacity = submission_capacity(db, owner, request.remote_addr or 'unknown', time.time())
            db.commit()
        return dict(ready=capacity is None, **(capacity or {}))

    @app.post('/malware')
    def support_submit():
        owner = submission_owner()
        values = {
            name: request.form.get(name, '').strip() for name in ('sender', 'subject', 'body')
        }
        values['terms_agreed'] = request.form.get('terms_agreed', '')

        def fail(message, status=400, code=None, retry_after=None):
            if request.accept_mimetypes.best == 'application/json':
                payload = dict(error=message)
                if code:
                    payload['code'] = code
                if retry_after is not None:
                    payload['retry_after'] = retry_after
                response = app.make_response((payload, status))
                if retry_after is not None:
                    response.headers['Retry-After'] = str(retry_after)
                return response
            if app.config.get('UPLOAD_SITE_ADDRESS'):
                return render_template(
                    'upload_receipt.html',
                    message=message,
                    result=None,
                    platform_url=app.config['SITE_ADDRESS'] + '/platform',
                ), status
            return render_template(
                'flag.html',
                title='Contact support',
                page='platform',
                flag=app.config['FLAG'],
                values=values,
                message=message,
            ), status

        attachments = [f for f in request.files.getlist('attachments') if f.filename]
        error = validate_submission(values, attachments)
        if error:
            return fail(error)
        now = time.time()
        sid = secrets.token_hex(16)
        created = datetime.now(timezone.utc)
        client = request.remote_addr or 'unknown'
        db = mailbox.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            db.execute(
                'DELETE FROM submission_attempts WHERE stamp<=? AND processing_until<=?',
                (now - 60, now),
            )
            db.execute('DELETE FROM submission_source_attempts WHERE stamp<=?', (now - 60,))
            capacity = submission_capacity(db, owner, client, now, enqueue=True)
            if capacity:
                db.commit()
                # This response is safe to retry: nothing has been admitted.
                return fail(capacity['error'], 429, capacity['code'], capacity.get('retry_after'))
            # Reserve both budgets atomically before costly work. Failures keep
            # their rate-limit slot; the processing lease expires after crashes.
            db.execute(
                'INSERT INTO submission_attempts VALUES (?, ?, ?, ?)',
                (sid, owner, now, now + config.SUPPORT_PROCESSING_LEASE_SECONDS),
            )
            db.execute('DELETE FROM submission_waiters WHERE owner=?', (owner,))
            db.execute('INSERT INTO submission_source_attempts VALUES (?, ?)', (client, now))
            db.commit()
            folder = mailbox.root / sid
            folder.mkdir(mode=0o700)
            try:
                msg = build_message(values, created)
                signals = screen_email(values, has_attachments=bool(attachments))
                reasons = []
                files = store_attachments(attachments, folder, msg, signals, reasons)
                screen_attachments(app, files, folder, signals, reasons)
                db.execute('BEGIN IMMEDIATE')
                count = db.execute('SELECT COUNT(*) FROM submissions').fetchone()[0]
                if count >= config.SUPPORT_MAX_SUBMISSIONS:
                    db.rollback()
                    shutil.rmtree(folder, ignore_errors=True)
                    return fail('Support queue is busy. Please try again later.', 429)
                metadata = dict(
                    id=sid,
                    created=created.isoformat(),
                    **values,
                    files=files,
                    status='pending',
                    state='new',
                    reasons=reasons,
                    signals=signals,
                    comment='',
                    manual_review=[f['name'] for f in files if f['manual_review']],
                    defender='Not scanned — review on Windows endpoint',
                )
                state = apply_automatic_rejection(metadata) or 'new'
                (folder / 'message.eml').write_bytes(msg.as_bytes())
                (folder / 'metadata.json').write_text(json.dumps(metadata, indent=2))
                db.execute(
                    'INSERT INTO submissions (id, created, client, stamp, metadata, state, summary) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (
                        sid,
                        created.isoformat(),
                        client,
                        now,
                        json.dumps(metadata),
                        state,
                        json.dumps(queue_summary(metadata)),
                    ),
                )
                if state == 'new':
                    # Snapshot the outstanding queue in the same transaction as
                    # this insert; completed/rejected reports are not remaining work.
                    pending_count = db.execute(
                        "SELECT COUNT(*) FROM submissions WHERE state='new'"
                    ).fetchone()[0]
                db.commit()
            except UploadTooLarge:
                db.rollback()
                shutil.rmtree(folder, ignore_errors=True)
                return fail('Each file and the combined attachments must be at most 20 MiB.', 413)
            except Exception:
                db.rollback()
                shutil.rmtree(folder, ignore_errors=True)
                raise
        finally:
            try:
                db.rollback()
                db.execute('UPDATE submission_attempts SET processing_until=0 WHERE id=?', (sid,))
                db.commit()
            finally:
                db.close()
        if state == 'new':
            notify_queue(app, metadata, pending_count)
        # Only the POST response contains the receipt. The reference grants no
        # read access, and no receipt is saved in the player's session.
        result = player_result(metadata)
        if request.accept_mimetypes.best == 'application/json':
            return result, 201
        if app.config.get('UPLOAD_SITE_ADDRESS'):
            return render_template(
                'upload_receipt.html',
                result=result,
                platform_url=app.config['SITE_ADDRESS'] + '/platform',
            )
        return render_template(
            'flag.html',
            title='Contact support',
            page='platform',
            flag=app.config['FLAG'],
            values={},
            result=result,
        )
