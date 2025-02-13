import json
import logging
from datetime import datetime

import croniter
import sqlalchemy.exc
from flask import (Blueprint, Response, current_app, flash, redirect, render_template,
                   request, url_for)
from flask_babel import gettext, lazy_gettext

from paper_eta.src import database, db, exts, forms, site_data, utils
from paper_eta.src.libs import hketa, renderer, refresher

bp = Blueprint('schedule',
               __name__,
               template_folder="../../../templates",
               url_prefix="/schedules")


@bp.route('/')
def index():
    if request.args.get("action") == "export":
        return Response(
            json.dumps(
                tuple(map(lambda s: s.as_dict(exclude=["id", "enabled", "bookmark_group_id"]),
                          database.Schedule.query.all())
                      ),
                indent=4),
            mimetype='application/json',
            headers={'Content-disposition': 'attachment; filename=schedules.json'})
    if request.headers.get('HX-Request'):
        schedules = []
        for schedule in database.Schedule.query.all():
            if schedule.enabled:
                schedule.next_execution = croniter.croniter(schedule.schedule, start_time=datetime.now())\
                    .get_next(datetime)\
                    .isoformat()
            else:
                schedule.next_execution = lazy_gettext("not_enabled")
            schedules.append(schedule)
        return Response(render_template("schedule/partials/rows.jinja", schedules=schedules),
                        headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

    return render_template("schedule/index.jinja")


@bp.route('/', methods=['POST'])
def import_():
    fields = ({c.name for c in database.Schedule.__table__.c} -
              {'id', 'enabled', 'bookmark_group_id', 'created_at', 'updated_at'})  # accepted fields for table inputs
    try:
        for i, schedule in enumerate(json.load(request.files['schedules'].stream)):
            # reference: https://stackoverflow.com/a/76799290
            with db.session.begin_nested() as session:
                try:
                    db.session.add(
                        database.Schedule(**{**{k: schedule[k] for k in fields}, 'enabled': False}))
                    db.session.flush()
                except (KeyError, TypeError, sqlalchemy.exc.StatementError) as e:
                    session.rollback()

                    flash(lazy_gettext('Failed to import no. %(entry)s schedule.', entry=i),
                          "error")
                    logging.exception('During schedule import: %s', str(e))
        db.session.commit()
    except (UnicodeDecodeError, json.decoder.JSONDecodeError):
        flash(lazy_gettext('import_failed'), "error")
    return redirect(url_for('schedule.index'))


@bp.route('/create', methods=["GET", "POST"])
def create():
    if not site_data.AppConfiguration().configurated():
        flash(lazy_gettext("missing_app_config"), "error")
        return redirect(url_for('schedule.index'))

    form = forms.ScheduleForm()

    if form.validate_on_submit():
        db.session.add(database.Schedule(**{k: v for k, v in form.data.items()
                                            if k not in ("csrf_token", "submit")}))
        db.session.commit()
        return redirect(url_for("schedule.index"))

    return render_template("schedule/form.jinja",
                           zip=zip,
                           list=list,
                           form=form,
                           formats=[c[0] for c in form.eta_format.choices],
                           )


@bp.route('/edit/<id_>', methods=["GET", "POST"])
def edit(id_: str):
    form = forms.ScheduleForm()
    sch: database.Schedule = database.Schedule.query.get_or_404(id_)

    if form.validate_on_submit():
        for k, v in form.data.items():
            setattr(sch, k, v)
        db.session.merge(sch)
        db.session.commit()
        return redirect(url_for("schedule.index"))

    form.schedule.data = sch.schedule
    form.bookmark_group_id.data = str(sch.bookmark_group_id)
    form.eta_format.data = sch.eta_format
    form.layout.data = sch.layout
    form.is_partial.data = sch.is_partial
    form.partial_cycle.data = sch.partial_cycle
    form.enabled.data = sch.enabled

    return render_template("schedule/form.jinja",
                           zip=zip,
                           list=list,
                           form=form,
                           formats=[c[0] for c in form.eta_format.choices],
                           )


@bp.route('/status/<id_>', methods=["PUT"])
def toggle_status(id_: str):
    try:
        schedule = database.Schedule.query.get(id_)
        setattr(schedule, "enabled", not schedule.enabled)
        db.session.commit()
        return Response(
            headers={
                "HX-Location": json.dumps({
                    "path": url_for("schedule.index"),
                    "target": "tbody",
                    "swap": "innerHTML"
                })}
        )
    except sqlalchemy.exc.SQLAlchemyError:
        return Response("", status=422, headers={"HX-Trigger": json.dumps({
            "toast": {
                "level": "error",
                "message": gettext("invalid_id")
            }
        })})


@bp.route('/<id_>', methods=["DELETE"])
def delete(id_: str):
    try:
        schedule = database.Schedule.query.get(id_)
        db.session.delete(schedule)
        db.session.commit()
        return Response(
            headers={
                "HX-Location": json.dumps({
                    "path": url_for("schedule.index"),
                    "target": "tbody",
                    "swap": "innerHTML"
                })}
        )
    except sqlalchemy.exc.SQLAlchemyError:
        return Response("", status=422, headers={"HX-Trigger": json.dumps({
            "toast": {
                "level": "error",
                "message": gettext("invalid_id")
            }
        })})


@bp.route("/layouts/<eta_format>")
def layouts(eta_format: str):
    if not (app_conf := site_data.AppConfiguration()).configurated():
        return Response(render_template("/schedule/partials/layout_radio.jinja",
                                        layouts=[],
                                        eta_format=eta_format),
                        headers={"HX-Trigger": json.dumps({
                            "toast": {
                                "level": "error",
                                "message": gettext("missing_app_config")
                            }
                        })})

    try:
        return render_template("/schedule/partials/layout_radio.jinja",
                               layouts=renderer.layouts(
                                   app_conf['epd_brand'], app_conf['epd_model'], eta_format),
                               eta_format=eta_format)
    except KeyError:
        return Response(render_template("/schedule/partials/layout_radio.jinja",
                                        layouts={},
                                        eta_format=eta_format),
                        headers={"HX-Trigger": json.dumps({
                            "toast": {
                                "level": "warning",
                                "message": gettext("No available layout for %(layout)s.", layout=gettext(eta_format))
                            }
                        })})


@bp.route("/preview/<eta_format>/<layout>")
def preview(eta_format: str, layout: str):
    if eta_format not in (t for t in renderer.EtaFormat):
        return Response("", status=422, headers={"HX-Trigger": json.dumps({
            "toast": {
                "level": "error",
                "message": f"{gettext('parameter_not_in_choice')}{gettext('.')}"
            }
        })})
    if not (app_conf := site_data.AppConfiguration()).configurated():
        return Response("", status=422, headers={"HX-Trigger": json.dumps({
            "toast": {
                "level": "error",
                "message": gettext("missing_app_config")
            }
        })})

    try:
        queries = [hketa.RouteQuery(**bm.as_dict())
                   for bm in database.Bookmark.query
                   .filter(database.Bookmark.enabled)
                   .filter(database.Bookmark.bookmark_group_id == (request.args.get("bookmark_group_id") or None))
                   .order_by(database.Bookmark.ordering)
                   .all()]

        etas = [
            exts.hketa.create_eta_processor(query).etas() for query in queries
        ]

        render = renderer.create(
            app_conf["epd_brand"], app_conf["epd_model"], eta_format, layout)
    except ModuleNotFoundError:
        return Response("", status=422, headers={"HX-Trigger": json.dumps({
            "toast": {
                "level": "error",
                "message": gettext("Layout does not exists.")
            }
        })})

    return render_template("schedule/partials/layout_preview.jinja",
                           image=utils.img2b64(renderer.merge(render.draw(etas))))


@ bp.route("/refresh/<id_>")
def refresh(id_: str):
    schedule: database.Schedule = database.Schedule.query.get_or_404(id_)

    if not (app_conf := site_data.AppConfiguration()).configurated():
        return Response("", status=422, headers={"HX-Trigger": json.dumps({
            "toast": {
                "level": "error",
                "message": gettext("missing_app_config")
            }
        })})

    try:
        success = refresher.refresh((database.Bookmark.query
                                    .filter(database.Bookmark.bookmark_group_id == schedule.bookmark_group_id)
                                    .all()),
                                    app_conf['epd_brand'],
                                    app_conf['epd_model'],
                                    schedule.eta_format.value,
                                    schedule.layout,
                                    schedule.is_partial,
                                    app_conf['degree'],
                                    app_conf['dry_run'],
                                    current_app.config['DIR_SCREEN_DUMP'])
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.critical("Unhandled exception: %s (%s)", str(e), e.__class__)
        return Response("", status=500, headers={"HX-Trigger": json.dumps({
            "toast": {
                "level": "error",
                "message": gettext("error")
            }
        })})

    if not success:
        return Response("", status=500, headers={"HX-Trigger": json.dumps({
            "toast": {
                "level": "error",
                "message": gettext("error")
            }
        })})
    return Response("", status=200, headers={"HX-Trigger": json.dumps({
        "toast": {
            "level": "success",
            "message": gettext("success")
        }
    })})
