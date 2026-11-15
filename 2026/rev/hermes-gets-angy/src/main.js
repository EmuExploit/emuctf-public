'use strict';

// toBytes
const a = (x) => {
  if (x instanceof Uint8Array) return x;
  if (typeof x === 'string') return new TextEncoder().encode(x);
  if (Array.isArray(x) || ArrayBuffer.isView(x)) return Uint8Array.from(x);
  throw new TypeError('expected Uint8Array, array or string');
};
// rotl32
const b = (x, n) => ((x << n) | (x >>> (32 - n))) >>> 0;

// xorInto
const c = (data, stream) => {
  const out = new Uint8Array(data.length);
  for (let i = 0; i < data.length; i++) out[i] = data[i] ^ stream[i];
  return out;
};

// rc4Keystream
function d(key, length, { drop = 0 } = {}) {
  key = a(key);
  if (key.length === 0) throw new RangeError('woof');
  const S = new Uint8Array(256);
  for (let i = 0; i < 256; i++) S[i] = i;
  for (let i = 0, j = 0; i < 256; i++) {
    j = (j + S[i] + key[i % key.length]) & 0xff;
    const t = S[i]; S[i] = S[j]; S[j] = t;
  }
  const out = new Uint8Array(length);
  for (let n = -drop, i = 0, j = 0; n < length; n++) {
    i = (i + 1) & 0xff;
    j = (j + S[i]) & 0xff;
    const t = S[i]; S[i] = S[j]; S[j] = t;
    if (n >= 0) out[n] = S[(S[i] + S[j]) & 0xff];
  }
  return out;
}

// rc4
function e(key, data, opts) {
  data = a(data);
  return c(data, d(key, data.length, opts));
}

const SIGMA = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574]; // "expand 32-byte k"
const TAU = [0x61707865, 0x3120646e, 0x79622d36, 0x6b206574];   // "expand 16-byte k"

// readU32LE
const f = (b, o) => (b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)) >>> 0;
// writeU32LE
const g = (b, o, v) => { b[o] = v; b[o + 1] = v >>> 8; b[o + 2] = v >>> 16; b[o + 3] = v >>> 24; };

/** One 64-byte Salsa20 block from a 16-word input state. */
// salsa20Core
function h(input) {
  const x = Uint32Array.from(input);
  // qr
  const i = (a0, b0, c0, d0) => {
    x[b0] ^= b((x[a0] + x[d0]) >>> 0, 7);
    x[c0] ^= b((x[b0] + x[a0]) >>> 0, 9);
    x[d0] ^= b((x[c0] + x[b0]) >>> 0, 13);
    x[a0] ^= b((x[d0] + x[c0]) >>> 0, 18);
  };
  for (let r = 0; r < 20; r += 2) {
    i(0, 4, 8, 12); i(5, 9, 13, 1); i(10, 14, 2, 6); i(15, 3, 7, 11); // columns
    i(0, 1, 2, 3); i(5, 6, 7, 4); i(10, 11, 8, 9); i(15, 12, 13, 14); // rows
  }
  const out = new Uint8Array(64);
  for (let i = 0; i < 16; i++) g(out, i * 4, (x[i] + input[i]) >>> 0);
  return out;
}

// salsa20Keystream
function j(key, nonce, length) {
  key = a(key); nonce = a(nonce);
  if (key.length !== 16 && key.length !== 32) throw new RangeError('wrrf');
  if (nonce.length !== 8) throw new RangeError('bark');
  const c = key.length === 32 ? SIGMA : TAU;
  const k2 = key.length === 32 ? 16 : 0;
  const st = new Uint32Array(16);
  st[0] = c[0]; st[5] = c[1]; st[10] = c[2]; st[15] = c[3];
  for (let i = 0; i < 4; i++) {
    st[1 + i] = f(key, i * 4);
    st[11 + i] = f(key, k2 + i * 4);
  }
  st[6] = f(nonce, 0);
  st[7] = f(nonce, 4);
  const out = new Uint8Array(length);
  for (let off = 0, ctr = 0; off < length; off += 64, ctr++) {
    st[8] = ctr; // st[9] (high counter word) stays 0
    const block = h(st);
    out.set(block.subarray(0, Math.min(64, length - off)), off);
  }
  return out;
}

/** Encrypt/decrypt (symmetric). Counter starts at 0, 20 rounds. */
// salsa20
function k(key, nonce, data) {
  data = a(data);
  return c(data, j(key, nonce, data.length));
}

// ---------------------------------------------------------------- TEA

const TEA_DELTA = 0x9e3779b9;

// Uint32Array => 4 key words as-is; anything else => 16 key bytes read little-endian.
// resolveTeaKey
const l = (key) => {
  if (key instanceof Uint32Array) {
    if (key.length !== 4) throw new RangeError('bork');
    return key;
  }
  const kb = a(key);
  if (kb.length !== 16) throw new RangeError('woof');
  return Uint32Array.of(f(kb, 0), f(kb, 4), f(kb, 8), f(kb, 12));
};

/** Encrypt one 64-bit block given as [v0, v1] uint32 words. k = 4 uint32 words. */
// teaEncryptBlock
function m(v, k) {
  let v0 = v[0] >>> 0, v1 = v[1] >>> 0, sum = 0;
  for (let i = 0; i < 32; i++) {
    sum = (sum + TEA_DELTA) >>> 0;
    v0 = (v0 + ((((v1 << 4) + k[0]) ^ (v1 + sum) ^ ((v1 >>> 5) + k[1])) >>> 0)) >>> 0;
    v1 = (v1 + ((((v0 << 4) + k[2]) ^ (v0 + sum) ^ ((v0 >>> 5) + k[3])) >>> 0)) >>> 0;
  }
  return [v0, v1];
}

// teaDecryptBlock
function n(v, k) {
  let v0 = v[0] >>> 0, v1 = v[1] >>> 0, sum = Math.imul(TEA_DELTA, 32) >>> 0;
  for (let i = 0; i < 32; i++) {
    v1 = (v1 - ((((v0 << 4) + k[2]) ^ (v0 + sum) ^ ((v0 >>> 5) + k[3])) >>> 0)) >>> 0;
    v0 = (v0 - ((((v1 << 4) + k[0]) ^ (v1 + sum) ^ ((v1 >>> 5) + k[1])) >>> 0)) >>> 0;
    sum = (sum - TEA_DELTA) >>> 0;
  }
  return [v0, v1];
}

// teaEcb
function o(encrypt, key, data) {
  data = a(data);
  if (data.length % 8) throw new RangeError('mrow');
  const k = l(key);
  const fn = encrypt ? m : n;
  const out = new Uint8Array(data.length);
  for (let o = 0; o < data.length; o += 8) {
    const [a, b] = fn([f(data, o), f(data, o + 4)], k);
    g(out, o, a); g(out, o + 4, b);
  }
  return out;
}

/** ECB over bytes, little-endian words. key: 16 bytes or Uint32Array(4) of words. */
// teaEncrypt
const p = (key, data) => o(true, key, data);
// teaDecrypt
const q = (key, data) => o(false, key, data);

// ---------------------------------------------------------------- AES

const AES_SBOX = new Uint8Array(256);
const AES_INV_SBOX = new Uint8Array(256);
// xtime
const r = (x) => ((x << 1) ^ (x & 0x80 ? 0x1b : 0)) & 0xff;
// gmul
const s = (a, b) => {
  let p = 0;
  for (; b; b >>= 1, a = r(a)) if (b & 1) p ^= a;
  return p;
};
(() => {
  // Walk GF(2^8) with generator 3 to get inverses, then apply the affine map.
  const exp = new Uint8Array(256), log = new Uint8Array(256);
  for (let i = 0, x = 1; i < 255; i++, x = s(x, 3)) { exp[i] = x; log[x] = i; }
  for (let i = 0; i < 256; i++) {
    const inv = i === 0 ? 0 : exp[(255 - log[i]) % 255];
    let s = inv;
    for (let r = 1; r < 5; r++) s ^= ((inv << r) | (inv >>> (8 - r))) & 0xff;
    s ^= 0x63;
    AES_SBOX[i] = s;
    AES_INV_SBOX[s] = i;
  }
})();

/** Expand a 16/24/32-byte key into (Nr+1) 16-byte round keys, flat. */
// aesExpandKey
function t(key) {
  key = a(key);
  const Nk = key.length / 4;
  if (![4, 6, 8].includes(Nk)) throw new RangeError('mrrp');
  const Nr = Nk + 6, total = 4 * (Nr + 1);
  const w = new Uint8Array(total * 4);
  w.set(key);
  let rcon = 1;
  for (let i = Nk; i < total; i++) {
    let t = w.slice((i - 1) * 4, i * 4);
    if (i % Nk === 0) {
      t = Uint8Array.of(AES_SBOX[t[1]] ^ rcon, AES_SBOX[t[2]], AES_SBOX[t[3]], AES_SBOX[t[0]]);
      rcon = r(rcon);
    } else if (Nk > 6 && i % Nk === 4) {
      t = t.map((b) => AES_SBOX[b]);
    }
    for (let j = 0; j < 4; j++) w[i * 4 + j] = w[(i - Nk) * 4 + j] ^ t[j];
  }
  return { roundKeys: w, rounds: Nr };
}

// addRoundKey
const u = (s, rk, r) => { for (let i = 0; i < 16; i++) s[i] ^= rk[r * 16 + i]; };

// State is column-major: s[c*4 + r].
// shiftRows
function v(s, inv) {
  const t = s.slice();
  for (let r = 1; r < 4; r++)
    for (let c = 0; c < 4; c++)
      s[c * 4 + r] = inv ? t[((c - r + 4) % 4) * 4 + r] : t[((c + r) % 4) * 4 + r];
}

// mixColumns
function w(state, inv) {
  const m = inv ? [14, 11, 13, 9] : [2, 3, 1, 1];
  for (let c = 0; c < 4; c++) {
    const column = state.slice(c * 4, c * 4 + 4);
    for (let r = 0; r < 4; r++)
      state[c * 4 + r] = s(column[0], m[(4 - r) % 4]) ^ s(column[1], m[(5 - r) % 4]) ^ s(column[2], m[(6 - r) % 4]) ^ s(column[3], m[(7 - r) % 4]);
  }
}

// aesEncryptBlock
function x(block, ks) {
  const state = Uint8Array.from(block), { roundKeys: rk, rounds: Nr } = ks;
  u(state, rk, 0);
  for (let r = 1; r <= Nr; r++) {
    for (let i = 0; i < 16; i++) state[i] = AES_SBOX[state[i]];
    v(state, false);
    if (r !== Nr) w(state, false);
    u(state, rk, r);
  }
  return state;
}

// aesDecryptBlock
function y(block, ks) {
  const state = Uint8Array.from(block), { roundKeys: rk, rounds: Nr } = ks;
  u(state, rk, Nr);
  for (let r = Nr - 1; r >= 0; r--) {
    v(state, true);
    for (let i = 0; i < 16; i++) state[i] = AES_INV_SBOX[state[i]];
    u(state, rk, r);
    if (r !== 0) w(state, true);
  }
  return state;
}

// aesBlock16
const z = (data) => {
  data = a(data);
  if (data.length !== 16) throw new RangeError('arf');
  return data;
};

/** Single 16-byte block in, 16-byte block out. */
// aesEcbEncrypt
const aa = (key, data) => x(z(data), t(key));
// aesEcbDecrypt
const ab = (key, data) => y(z(data), t(key));

// ---------------------------------------------------------------- FNV-1a

const FNV_OFFSET = 0x811c9dc5;
const FNV_PRIME = 0x01000193;

/** Streaming FNV-1a 32: every byte is absorbed immediately, so no input is ever buffered. */
// FNV1a
class ac {
  constructor() {
    this.h = FNV_OFFSET;
  }

  update(data) {
    data = a(data);
    for (let i = 0; i < data.length; i++) this.h = Math.imul(this.h ^ data[i], FNV_PRIME) >>> 0;
    data.fill(0); // wipe the chunk so it doesn't linger on the heap
    return this;
  }

  digest() {
    return this.h;
  }
}

const digest = new ac().update(
	e("emuexp>skibidogs", Uint8Array.fromHex("17b2811c20b4ac70"))
).update(
	k("emusover roombas", [0,0,0,0,0,0,0,0], Uint8Array.fromHex("9c0cf74c609fff9586"))
).update(
	q("emusbttrthnbears", Uint8Array.fromHex("f04e5ec98c0777be"))
).update(
	ab("hi - nullvoidptr", Uint8Array.fromHex("d57eaffa809185ae67c4de0af1c6d7a3"))
).digest();

if (digest === 0x4e1bcad2) {
  print("Hash matched");
}
