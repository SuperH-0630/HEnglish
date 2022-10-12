from flask import blueprints, render_template, current_app, abort, redirect, url_for, flash, make_response, request
from flask_login import current_user, login_required
from app.user import UserWordDataBase

word_list = blueprints.Blueprint("word_list", __name__)


def __load_word_list(res, page, page_count, word_list_title, url, up_url, next_url):
    if res is None or (page != 1 and page > page_count):
        abort(400)
    word = []
    for i in res:
        item = [i[1], i[0], i[2], i[3], i[4], ""]
        for ec in i[5].split("@@"):
            ec = ec.strip()
            if ec == "##" or len(ec) == 0:
                continue
            e, c = ec.split("##")
            e = e.strip()
            c = c.strip()
            item[5] += f"{e} {c}<br>"
        word.append(item)
    if page == 1:
        up_url = ""
    if page >= page_count:
        next_url = ""
    return render_template("word_list.html",
                           word=word,
                           page_count=page_count,
                           page=page, up_url=up_url, next_url=next_url,
                           word_list_title=word_list_title, url=url, len=len)


@word_list.route("/")
@login_required
def show_all_word():
    user: UserWordDataBase = current_user
    try:
        page = int(request.args.get("page", 1))
    except (ValueError, TypeError):
        return abort(400)
    if page < 1:
        abort(400)
    res = user.search("SELECT word, box, part, english, chinese, eg FROM main.Word "
                      "ORDER BY word, box "
                      "LIMIT 20 OFFSET ?", (page - 1) * 20)
    word_count = user.search("SELECT COUNT(id) FROM main.Word")[0][0]
    page_count = word_count // 20
    if word_count % 20 > 0:
        page_count += 1
    return __load_word_list(res, page, page_count, f"All Word: {page}",
                            url_for("word_list.show_all_word"),
                            url_for("word_list.show_all_word", page=page - 1),
                            url_for("word_list.show_all_word", page=page + 1))


@word_list.route("/box/<int:box>")
@login_required
def show_box_word(box: int):
    user: UserWordDataBase = current_user
    if box < 0 or box > 5:
        abort(400)
    try:
        page = int(request.args.get("page", 1))
    except (ValueError, TypeError):
        return abort(400)
    if page < 1:
        abort(400)
    res = user.search("SELECT word, box, part, english, chinese, eg FROM main.Word WHERE box=? "
                      "ORDER BY word, box LIMIT 20 OFFSET ?", box, (page - 1) * 20)
    word_count = user.search("SELECT COUNT(id) FROM main.Word WHERE box=?", box)[0][0]
    page_count = word_count // 20
    if word_count % 20 > 0:
        page_count += 1
    return __load_word_list(res, page, page_count, f"Box{box} Word: {page}",
                            url_for("word_list.show_box_word", box=box),
                            url_for("word_list.show_box_word", box=box, page=page - 1),
                            url_for("word_list.show_box_word", box=box, page=page + 1))

