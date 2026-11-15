randomize();
display_reset(0, true);

ini_open("emu.ini");
global.hi = ini_read_real("score", "hi", 0);
ini_close();

ground = room_height - 64;
emu = { x: 120, y: ground, vy: 0, on_ground: true, leg: 0 };
obstacles = [];
spd = 6;
pts = 0;
scroll = 0;
dead = false;

// jump physics
jump_vy = -13;
grav = 0.65;
hit_w = sprite_get_width(spr_emu_run) * 0.6;

// measure the jump: frames airborne, and frames high enough to clear a rock
var tall_h = max(sprite_get_height(spr_rock_small), sprite_get_height(spr_rock_tall));
var h = 0, v = -jump_vy;
air_frames = 0;
clear_frames = 0;
repeat (200) {
    v -= grav;
    h += v;
    if (h <= 0) break;
    air_frames++;
    if (h >= tall_h - 6) clear_frames++;
}

// spawning
since_spawn = 0;
next_gap = 400;
last_pair = false;
group_len = 0;
react_frames = 12;
jump_tol = 8;

// day/night cycle
night = 0;
stars = [];
repeat (40) {
    array_push(stars, { x: irandom(room_width), y: irandom(ground - 60) });
}