#!/usr/bin/env python3
"""render_css.py -- turns one design_tokens.py token dict into real CSS
text, for each CSS "family" actually found on disk across the 43 built
apps. A family is a distinct set of selectors a generated app's inline
<style> block uses for the same semantic roles (card, heading, button,
danger button, secondary button, list, list item, input/select/textarea,
row layout). generate_skins.py discovers which family each app belongs to
by hashing its own style block -- this file never guesses a selector that
isn't proven, by that hash, to exist in the app it will be applied to.

Two families exist today (found by inspecting every one of the 43 apps'
own generated HTML, not assumed):
  - "shared_card"  -- 42 of 43 apps, byte-identical inline CSS (the
    gen_common.py host convention: body/.card/h1/input,select,textarea/
    button/button.danger/button.secondary/ul/li/.row).
  - "todomvc"      -- todo_list only, its own bespoke TodoMVC-style
    selectors (.todoapp/#new-todo/ul#todo-list li/.toggle/.destroy/...).

Adding a new app whose generator produces a third selector set means
adding a third FAMILY_RENDERERS entry here -- never bending an existing
family's CSS to half-match a selector set it wasn't measured against.
"""
from typing import Dict


def render_shared_card(tok: Dict) -> str:
    return f"""
body {{ font-family: {tok['font_body']}; max-width: {tok['body_max_width']}; margin: 40px auto;
  color: {tok['foreground']}; background: {tok['background']}; }}
.card {{ background: {tok['surface']}; box-shadow: {tok['shadow_card']}; border: 1px solid {tok['border']};
  border-radius: {tok['radius']}; padding: {tok['card_padding']}; margin-bottom: {tok['card_gap']}; }}
h1 {{ font-family: {tok['font_heading']}; font-weight: {tok['heading_weight']}; font-size: 22px;
  color: {tok['foreground']}; }}
input, select, textarea {{ font-family: {tok['font_body']}; font-size: 15px; padding: {tok['input_padding']};
  border: {tok['input_border']}; border-radius: {tok['radius_sm']}; box-sizing: border-box;
  background: {tok['surface']}; color: {tok['foreground']}; }}
input:focus, select:focus, textarea:focus {{ outline: none; border-color: {tok['primary']};
  box-shadow: {tok['shadow_focus_ring']}; }}
button {{ font-family: {tok['font_body']}; font-size: 14px; font-weight: {tok['button_font_weight']};
  padding: {tok['button_padding']}; border: none; border-radius: {tok['radius_pill']};
  background: {tok['primary']}; color: {tok['primary_foreground']}; cursor: pointer;
  transition: background-color .12s ease; }}
button:hover {{ background: {tok['primary_hover']}; }}
button:focus-visible {{ outline: none; box-shadow: {tok['shadow_focus_ring']}; }}
button.danger {{ background: {tok['danger']}; color: #ffffff; }}
button.secondary {{ background: {tok['secondary_button']}; color: {tok['secondary_button_foreground']}; }}
ul {{ list-style: none; margin: 0; padding: 0; }}
li {{ border-bottom: 1px solid {tok['border']}; padding: 10px 4px; color: {tok['foreground']}; }}
.row {{ display: flex; gap: {tok['row_gap']}; align-items: center; flex-wrap: wrap; }}
""".strip("\n")


def render_todomvc(tok: Dict) -> str:
    return f"""
body {{ font-family: {tok['font_body']}; max-width: 550px; margin: 40px auto;
  color: {tok['foreground']}; background: {tok['background']}; }}
.todoapp {{ background: {tok['surface']}; box-shadow: {tok['shadow_card']}; border: 1px solid {tok['border']};
  border-radius: {tok['radius']}; }}
.header input#new-todo {{ width: 100%; box-sizing: border-box; font-family: {tok['font_body']};
  font-size: 20px; padding: 12px; border: none; border-bottom: 1px solid {tok['border']};
  background: {tok['surface']}; color: {tok['foreground']}; }}
.header input#new-todo:focus {{ outline: none; box-shadow: inset {tok['shadow_focus_ring']}; }}
ul#todo-list {{ list-style: none; margin: 0; padding: 0; }}
ul#todo-list li {{ position: relative; border-bottom: 1px solid {tok['border']};
  padding: 12px 12px 12px 40px; color: {tok['foreground']}; }}
ul#todo-list li .toggle {{ position: absolute; left: 10px; top: 14px; accent-color: {tok['primary']}; }}
ul#todo-list li label {{ margin-left: 6px; }}
ul#todo-list li.completed label {{ text-decoration: line-through; color: {tok['muted_foreground']}; }}
ul#todo-list li .destroy {{ display: none; float: right; cursor: pointer; border: none; background: none;
  color: {tok['danger']}; }}
ul#todo-list li:hover .destroy {{ display: inline; }}
ul#todo-list li .edit {{ display: none; width: 90%; font-size: 16px; }}
ul#todo-list li.editing .edit {{ display: inline; }}
ul#todo-list li.editing .view {{ display: none; }}
.footer {{ padding: 10px 15px; display: flex; justify-content: space-between; align-items: center;
  color: {tok['muted_foreground']}; }}
.footer .filters {{ list-style: none; display: inline-flex; gap: 8px; margin: 0; padding: 0; }}
.footer .filters a {{ text-decoration: none; color: {tok['muted_foreground']}; padding: 2px 6px;
  border: 1px solid transparent; border-radius: {tok['radius_sm']}; }}
.footer .filters a.selected {{ border-color: {tok['primary']}55; }}
#clear-completed {{ border: none; background: none; cursor: pointer; color: {tok['muted_foreground']}; }}
""".strip("\n")


FAMILY_RENDERERS = {
    "shared_card": render_shared_card,
    "todomvc": render_todomvc,
}


def render(family: str, tok: Dict) -> str:
    fn = FAMILY_RENDERERS.get(family)
    if fn is None:
        raise ValueError(f"no CSS renderer registered for family {family!r} -- "
                          f"known families: {sorted(FAMILY_RENDERERS)}. Never guess; add one.")
    return fn(tok)
