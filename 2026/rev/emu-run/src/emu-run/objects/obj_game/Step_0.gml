if (dead) {
    if (keyboard_check_pressed(vk_space)) room_restart();
    exit;
}

// day/night: switches every 20 rocks (day 0-19, night 20-39, day 40-59, ...)
var is_night = (floor(pts / 20) mod 2 == 1);
night = lerp(night, is_night ? 1 : 0, 0.02);

var d = clamp(pts / 40, 0, 1);   // difficulty 0..1
spd = min(6 + pts * 0.3, 16);
scroll = (scroll + spd) mod 64;

if (emu.on_ground && (keyboard_check_pressed(vk_space) || keyboard_check_pressed(vk_up))) {
    emu.vy = jump_vy;
    emu.on_ground = false;
}
emu.vy += grav;
emu.y += emu.vy;
if (emu.y >= ground) {
    emu.y = ground;
    emu.vy = 0;
    emu.on_ground = true;
}
emu.leg += spd * 0.03;

// spawn by distance travelled
since_spawn += spd;
if (since_spawn >= next_gap) {
    array_push(obstacles, { x: room_width + 20, spr: choose(spr_rock_small, spr_rock_tall), scored: false });
    since_spawn = 0;

    // if the gap just used was a pair gap, the emu jumps both rocks together
    group_len = last_pair ? next_gap : 0;

    react_frames = lerp(12, 4, d);
    jump_tol = lerp(8, 4, d);
    var extra = lerp(450, 100, d);
    var pair_chance = lerp(20, 45, d);

    // speed the next rock will have when it reaches the emu
    var ahead = 0;
    for (var k = 0; k < array_length(obstacles); k++) {
        if (!obstacles[k].scored) ahead++;
    }
    var spd_arrive = min(6 + (pts + ahead) * 0.3, 16);
    var min_sep = spd_arrive * (air_frames + react_frames);

    var max_w = max(sprite_get_width(spr_rock_small), sprite_get_width(spr_rock_tall));
    var pair_min = max_w + 24;
    var pair_max = (clear_frames - jump_tol) * spd - hit_w - max_w + 8;

    if (!last_pair && pts >= 2 && pair_max >= pair_min && irandom(99) < pair_chance) {
        next_gap = irandom_range(floor(pair_min), floor(pair_max));
        last_pair = true;
    } else {
        var lo = ceil(min_sep - group_len);
        next_gap = irandom_range(lo, lo + extra);
        last_pair = false;
    }
}

var ew = sprite_get_width(spr_emu_run), eh = sprite_get_height(spr_emu_run);
var el = emu.x - ew * 0.3, er = emu.x + ew * 0.3;
var et = emu.y - eh * 0.9, eb = emu.y - 2;

for (var i = array_length(obstacles) - 1; i >= 0; i--) {
    var o = obstacles[i];
    o.x -= spd;
    var ow = sprite_get_width(o.spr), oh = sprite_get_height(o.spr);
    if (o.x + ow < 0) {
        array_delete(obstacles, i, 1);
        continue;
    }

    // cleared: rock's right edge is behind the emu's left edge
    if (!o.scored && o.x + ow < el) {
        o.scored = true;
        pts += 1;
    }

    if (er > o.x + 4 && el < o.x + ow - 4 && eb > ground - oh + 4 && et < ground) {
        dead = true;
        if (floor(pts) > global.hi) {
            global.hi = floor(pts);
            ini_open("emu.ini");
            ini_write_real("score", "hi", global.hi);
            ini_close();
        }
    }
}