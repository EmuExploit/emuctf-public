"""Reviewer-only authentication, queue, mutations, preview and downloads."""

import hmac
import io
import json
import secrets
import time
import zipfile
from contextlib import closing

import nh3
from flask import Response, abort, redirect, render_template, request, send_file, session, url_for

from support import config
from support.auth import csrf_valid, reviewer_logged_in
from support.mail_screening import screening_report, screening_tags
from support.models import ADMIN_PATH, REVIEW_STATES, apply_automatic_rejection, review_tab

PREVIEW_TAGS = {
    'p',
    'br',
    'div',
    'span',
    'b',
    'strong',
    'i',
    'em',
    'u',
    's',
    'ul',
    'ol',
    'li',
    'blockquote',
    'pre',
    'code',
    'h1',
    'h2',
    'h3',
    'h4',
    'hr',
    'table',
    'thead',
    'tbody',
    'tr',
    'th',
    'td',
}


def register_reviewer_routes(app, mailbox):
    password = config.SUPPORT_ADMIN_PASSWORD
    root = mailbox.root

    @app.route(ADMIN_PATH + '/login', methods=['GET', 'POST'])
    def support_login():
        if reviewer_logged_in():
            return redirect(url_for('support_admin'))
        session.setdefault('review_csrf', secrets.token_hex(32))
        error, status = None, 200
        if request.method == 'POST':
            if not csrf_valid():
                abort(403)
            client, now = request.remote_addr or 'unknown', time.time()
            with closing(mailbox.connect()) as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute(
                    'DELETE FROM review_login_attempts WHERE stamp < ?',
                    (now - config.REVIEW_LOGIN_WINDOW_SECONDS,),
                )
                attempts = db.execute(
                    'SELECT COUNT(*) FROM review_login_attempts WHERE client=?', (client,)
                ).fetchone()[0]
                if attempts >= config.REVIEW_LOGIN_MAX_ATTEMPTS:
                    error, status = 'Try again later.', 429
                elif password and hmac.compare_digest(
                    request.form.get('password', '').encode(), password.encode()
                ):
                    session['review_authenticated_at'] = now
                    session['review_csrf'] = secrets.token_hex(32)
                    db.execute('DELETE FROM review_login_attempts WHERE client=?', (client,))
                    db.commit()
                    return redirect(url_for('support_admin'), code=303)
                else:
                    db.execute('INSERT INTO review_login_attempts VALUES (?, ?)', (client, now))
                    error, status = 'Incorrect password.', 401
                db.commit()
        return render_template('support_login.html', error=error), status

    @app.post(ADMIN_PATH + '/logout')
    def support_logout():
        if not csrf_valid():
            abort(403)
        session.pop('review_authenticated_at', None)
        session.pop('review_csrf', None)
        return redirect(url_for('support_login'), code=303)

    @app.get(ADMIN_PATH)
    def support_admin():
        session.setdefault('review_csrf', secrets.token_hex(32))
        return render_template(
            'support_admin.html',
            admin_path=ADMIN_PATH,
            states=REVIEW_STATES,
            comment_limit=config.SUPPORT_COMMENT_MAX_LENGTH,
        )

    @app.get(ADMIN_PATH + '/api/submissions')
    def support_queue():
        tab = request.args.get('tab', 'queue')
        conditions = {
            'queue': "state = 'new'",
            'accepted': "state = 'flag'",
            'rejected': "state NOT IN ('new', 'flag')",
        }
        if tab not in conditions:
            abort(400)
        prefix = request.args.get('prefix', '').strip().lower()
        if len(prefix) > 32 or any(char not in '0123456789abcdef' for char in prefix):
            return {'error': 'Invalid reference prefix'}, 400
        mailbox.screen_pending_queue()
        # Searching a player reference covers every review state.
        condition = 'id GLOB ?' if prefix else conditions[tab]
        args = [prefix + '*'] if prefix else []
        with closing(mailbox.connect()) as db:
            counts = {'queue': 0, 'rejected': 0, 'accepted': 0}
            for state, count in db.execute(
                'SELECT state, COUNT(*) FROM submissions GROUP BY state'
            ):
                counts[review_tab(state)] += count
            before = request.args.get('before')
            if before:
                cursor = db.execute(
                    'SELECT stamp, id FROM submissions WHERE id=?', (before,)
                ).fetchone()
                if cursor is None:
                    abort(400)
                condition += ' AND (stamp < ? OR (stamp = ? AND id < ?))'
                args.extend([cursor[0], cursor[0], cursor[1]])
            rows = db.execute(
                f'SELECT summary, state FROM submissions WHERE {condition} ORDER BY stamp DESC, id DESC LIMIT 51',
                args,
            ).fetchall()
        items = [{**json.loads(raw), 'state': state} for raw, state in rows[:50]]
        return dict(
            items=items, counts=counts, next_cursor=items[-1]['id'] if len(rows) > 50 else None
        )

    def read_submission(sid):
        mailbox.screen_pending_queue()
        with closing(mailbox.connect()) as db:
            row = db.execute(
                'SELECT metadata, state, client FROM submissions WHERE id=?', (sid,)
            ).fetchone()
        if row is None:
            abort(404)
        meta = json.loads(row[0])
        return {**meta, 'state': row[1], 'client': row[2], 'comment': meta.get('comment', '')}

    @app.get(ADMIN_PATH + '/api/submissions/<sid>')
    def support_detail(sid):
        meta = read_submission(sid)
        meta['screening'] = screening_report(meta)
        meta['tags'] = screening_tags(report=meta['screening'])
        meta['preview_url'] = url_for('support_preview', sid=sid)
        meta['email_url'] = url_for('support_download', sid=sid, filename='message.eml')
        meta['zip_url'] = url_for('support_download', sid=sid, filename='attachments.zip')
        meta['metadata_url'] = url_for('support_download', sid=sid, filename='metadata.json')
        for item in meta['files']:
            item['download_url'] = url_for('support_download', sid=sid, filename=item['stored'])
        return meta

    @app.post(ADMIN_PATH + '/api/submissions/<sid>/state')
    def support_state(sid):
        if not csrf_valid():
            abort(403)
        payload = request.get_json(silent=True)
        state = payload.get('state') if isinstance(payload, dict) else None
        if not isinstance(state, str) or state not in REVIEW_STATES:
            return {'error': 'Invalid state'}, 400
        with closing(mailbox.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT metadata FROM submissions WHERE id=?', (sid,)).fetchone()
            if row is None:
                abort(404)
            meta = json.loads(row[0])
            if state == 'new':
                state = apply_automatic_rejection(meta) or 'new'
            meta.update(
                state=state,
                status='pending'
                if state == 'new'
                else 'accepted'
                if state == 'flag'
                else 'rejected',
            )
            db.execute(
                'UPDATE submissions SET state=?, metadata=? WHERE id=?',
                (state, json.dumps(meta), sid),
            )
            db.commit()
        return {'state': state, 'auto_rejection': meta.get('auto_rejection')}

    @app.post(ADMIN_PATH + '/api/submissions/<sid>/comment')
    def support_comment(sid):
        if not csrf_valid():
            abort(403)
        payload = request.get_json(silent=True)
        comment = payload.get('comment') if isinstance(payload, dict) else None
        if not isinstance(comment, str) or len(comment) > config.SUPPORT_COMMENT_MAX_LENGTH:
            return {'error': 'Invalid comment'}, 400
        with closing(mailbox.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT metadata FROM submissions WHERE id=?', (sid,)).fetchone()
            if row is None:
                abort(404)
            meta = json.loads(row[0])
            meta['comment'] = comment
            db.execute('UPDATE submissions SET metadata=? WHERE id=?', (json.dumps(meta), sid))
            db.commit()
        return {'comment': comment}

    @app.get(ADMIN_PATH + '/preview/<sid>')
    def support_preview(sid):
        meta = read_submission(sid)
        # No URLs, styles, images, forms, scripts, SVG or attacker-controlled attributes.
        # The sandbox and network-denying CSP remain even if sanitization ever fails.
        cleaned = nh3.clean(
            meta['body'],
            tags=PREVIEW_TAGS,
            attributes={},
            clean_content_tags={'script', 'style', 'iframe', 'object', 'svg', 'math', 'template'},
            link_rel=None,
        )
        response = Response(
            render_template('support_preview.html', cleaned=cleaned), mimetype='text/html'
        )
        response.headers['Content-Security-Policy'] = (
            "default-src 'none'; style-src 'unsafe-inline'; sandbox; frame-ancestors 'self'; base-uri 'none'; form-action 'none'"
        )
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    @app.get(ADMIN_PATH + '/<sid>/<filename>')
    def support_download(sid, filename):
        meta = read_submission(sid)
        if filename == 'attachments.zip':
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as bundle:
                for item in meta['files']:
                    # Numbered server-generated names avoid traversal and collisions.
                    bundle.write(root / sid / item['stored'], arcname=item['stored'])
            archive.seek(0)
            return send_file(
                archive,
                as_attachment=True,
                download_name=f'{sid}-attachments.zip',
                mimetype='application/zip',
            )
        allowed = {'message.eml', 'metadata.json'} | {f['stored'] for f in meta['files']}
        if filename not in allowed:
            abort(404)
        if filename == 'metadata.json':
            return Response(
                json.dumps(meta, indent=2),
                mimetype='application/octet-stream',
                headers={'Content-Disposition': f'attachment; filename="{sid}-metadata.json"'},
            )
        return send_file(
            root / sid / filename, as_attachment=True, mimetype='application/octet-stream'
        )
