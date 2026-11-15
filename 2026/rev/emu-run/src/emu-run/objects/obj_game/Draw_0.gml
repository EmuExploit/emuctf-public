// sky
draw_clear(merge_color(make_color_rgb(249, 181, 76), make_color_rgb(14, 18, 40), night));

// stars + moon
if (night > 0.02) {
    draw_set_alpha(night);
    draw_set_color(c_white);
    for (var s = 0; s < array_length(stars); s++) {
        draw_rectangle(stars[s].x, stars[s].y, stars[s].x + 1, stars[s].y + 1, false);
    }
    draw_set_color(make_color_rgb(235, 235, 215));
    draw_circle(room_width - 120, 70, 18, false);
    draw_set_alpha(1);
}

var tint = merge_color(c_white, make_color_rgb(120, 130, 180), night);

// ground
draw_set_color(merge_color(make_color_rgb(170, 80, 45), make_color_rgb(45, 28, 35), night));
draw_rectangle(0, ground + 64, room_width, room_height, false);
for (var gx = -floor(scroll); gx < room_width; gx += 64) {
    draw_sprite_ext(spr_ground, 0, gx, ground, 1, 1, 0, tint, 1);
}

// rocks (own tint so night contrast is tunable separately)
var rock_tint = merge_color(c_white, make_color_rgb(175, 180, 220), night);
for (var i = 0; i < array_length(obstacles); i++) {
    var o = obstacles[i];
    draw_sprite_ext(o.spr, 0, round(o.x), ground, 1, 1, 0, rock_tint, 1);
}

// emu
var spr = spr_emu_run, frame = floor(emu.leg);
if (dead) spr = spr_emu_dead;
else if (!emu.on_ground) spr = spr_emu_jump;
draw_sprite_ext(spr, frame, round(emu.x), round(emu.y), 1, 1, 0, merge_color(c_white, make_color_rgb(215, 215, 235), night), 1);

// HUD
draw_set_font(-1);
draw_set_alpha(1);
draw_set_color(merge_color(c_black, c_white, night));
draw_set_valign(fa_top);
draw_set_halign(fa_left);
draw_text(10, 10, "Score: " + string(floor(pts)));
draw_text(10, 30, "Best: " + string(max(global.hi, floor(pts))));

if (dead) {
    draw_set_halign(fa_center);
    draw_text(room_width / 2, room_height / 2 - 10, "GAME OVER - SPACE to restart");
    draw_set_halign(fa_left);
}