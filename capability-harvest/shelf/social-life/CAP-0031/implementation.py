# Harvested by harvest_parts.py
# capability : CAP-0031 (paginate list)
# from       : social-life @ 22c8625704b2e600fe69e94b26570c2cb1bf8abe
# source     : app.py:16-26
# licence    : Apache-2.0 (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def index():
    page = request.args.get("page", type=int)
    posts = Post.query.order_by(Post.date.desc()).paginate(page=page, per_page=ROWS_PER_PAGE)
    users = User.query.filter(User.id != current_user.id).limit(4).all()

    if request.headers.get("HX-Request"):
        return render_template("post/index.html", user=current_user, posts=posts, current_page=page)

    return render_template(
        "main.html", user=current_user, posts=posts, users=users, current_page=page
    )
