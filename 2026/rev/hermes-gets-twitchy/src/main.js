function a(input) {
  if (typeof input !== 'string') {
    throw new Error('wrrf');
  }

  const encoded = input.replace(/\s/g, '').toUpperCase();
  const paddingStart = encoded.indexOf('=');
  const payload = paddingStart === -1 ? encoded : encoded.slice(0, paddingStart);
  const padding = paddingStart === -1 ? '' : encoded.slice(paddingStart);

  if (!/^=*$/.test(padding) || (padding && encoded.length % 8 !== 0)) {
    throw new Error('woof');
  }

  const remainder = payload.length % 8;
  const expectedPadding = new Map([[0, 0], [2, 6], [4, 4], [5, 3], [7, 1]]);
  if (!expectedPadding.has(remainder) || (padding && padding.length !== expectedPadding.get(remainder))) {
    throw new Error('mrrp');
  }

  const bytes = [];
  let buffer = 0;
  let bits = 0;

  for (const character of payload) {
    const value = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'.indexOf(character);
    if (value === -1) {
      throw new Error('meow');
    }

    buffer = (buffer << 5) | value;
    bits += 5;

    while (bits >= 8) {
      bits -= 8;
      bytes.push((buffer >> bits) & 0xff);
    }

    buffer &= bits === 0 ? 0 : (1 << bits) - 1;
  }

  if (buffer !== 0) {
    throw new Error('mrow');
  }

  return new TextDecoder().decode(new Uint8Array(bytes));
}

function b(input) {
  if (typeof input !== 'string') {
    throw new Error('bark');
  }

  const encoded = input.replace(/\s/g, '');
  if (encoded.length % 2 !== 0 || !/^[0-9a-fA-F]*$/.test(encoded)) {
    throw new Error('bork');
  }

  return new TextDecoder().decode(Uint8Array.fromHex(encoded));
}

function c(input) {
  if (typeof input !== 'string') {
    throw new Error('mrrw');
  }

  return input.replace(/[A-Za-z]/g, (character) => {
    const start = character <= 'Z' ? 65 : 97;
    return String.fromCharCode(start + ((character.charCodeAt(0) - start + 13) % 26));
  });
}

function d(input) {
  if (typeof input !== 'string') {
    throw new Error('hi wednesday');
  }

  const encoded = input.replace(/\s/g, '');
  if (encoded.length % 2 !== 0 || !/^[0-9a-fA-F]*$/.test(encoded)) {
    throw new Error('emus > dogs');
  }

  const decoded = Uint8Array.fromHex(encoded);
  for (let index = 0; index < decoded.length; index += 1) {
    decoded[index] ^= 67;
  }

  return new TextDecoder().decode(decoded);
}

console.log(void (a("IVGVK63DGRXDOXY=") + b("636875636b5f") + c("guvf_vagb") + d("1c242b722731773e")));
