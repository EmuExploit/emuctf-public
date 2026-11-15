// Get references to the logo and button elements
var logo = document.getElementById('logo');
var button = document.querySelector('button');
const stonkElement = document.getElementById("xssbot-vid");
const audioElement2 = document.getElementById("monkenoise");
const audioElement3 = document.getElementById("audio1");
const audioElement4 = document.getElementById("audio2");
const content = document.querySelector(".container-hidden");
var invisibleElements = document.querySelectorAll('.meme');
const imageContainer = document.getElementById('imageContainer');



const body = document.body;




let currentBackgroundIndex = 0;

var junk = ['🙈','🙉','🙊','🐒','🍌','💸','📈','🔒','🛡','💀','🤡','✨','🚀','💰','🥴','👹','🫠'];
function spawn(){
  var e = document.createElement('div');
  e.textContent = junk[Math.floor(Math.random()*junk.length)];
  e.style.position = 'fixed';
  e.style.left = (Math.random()*100) + 'vw';
  e.style.top = '-8vh';
  e.style.fontSize = (Math.random()*44 + 22) + 'px';
  e.style.zIndex = 99990;
  e.style.pointerEvents = 'none';
  e.style.transition = 'transform 4s linear, opacity 4s linear';
  document.body.appendChild(e);
  requestAnimationFrame(function(){
    e.style.transform = 'translateY(118vh) rotate(' + (Math.random()*1080 - 540) + 'deg)';
    e.style.opacity = '0';
  });
  setTimeout(function(){ e.remove(); }, 4300);
}

function blastAllMedia(){
  var media = document.querySelectorAll('audio, video');
  for (var k = 0; k < media.length; k++) {
    try { media[k].volume = 1; media[k].play(); } catch (e) {}
  }
}

let chaosStarted = false;
function startChaos(){
  if (chaosStarted) return;
  chaosStarted = true;
  document.body.classList.add('unleashed');

  for (var i = 0; i < invisibleElements.length; i++) {
    invisibleElements[i].style.display = 'block';
  }

  try { stonkElement.play(); } catch (e) {}
  try { audioElement2.play(); } catch (e) {}
  try { audioElement3.play(); } catch (e) {}
  try { audioElement4.play(); } catch (e) {}
  blastAllMedia();
  document.addEventListener('pointerdown', blastAllMedia);
  document.addEventListener('keydown', blastAllMedia);

  setInterval(function(){
    document.title = document.title.split('').sort(function(){return 0.5-Math.random()}).join('');
  }, 200);

  setInterval(spawn, 160);
  setInterval(spawn, 55);

  setInterval(function(){
    var imgs = document.querySelectorAll('.monkes, .floaty, #logo img, .stormmonke');
    for (var k = 0; k < imgs.length; k++) {
      if (Math.random() < 0.25) {
        imgs[k].style.filter = 'hue-rotate(' + Math.floor(Math.random()*360) + 'deg) saturate(4) contrast(1.6)';
      }
    }
  }, 220);

  var tilt = 0;
  setInterval(function(){
    tilt = (Math.random() * 4) - 2;
    document.body.style.setProperty('zoom', (0.96 + Math.random()*0.08).toString());
    var cf = document.querySelector('.container-fluid');
    if (cf) cf.style.transform = 'rotate(' + tilt + 'deg)';
  }, 300);

  setInterval(function(){
    var storm = document.querySelectorAll('.stormmonke');
    for (var k = 0; k < storm.length; k++) {
      if (Math.random() < 0.08) {
        storm[k].style.top = (Math.random()*100) + 'vh';
        storm[k].style.left = (Math.random()*100) + 'vw';
        storm[k].style.filter = 'hue-rotate(' + Math.floor(Math.random()*360) + 'deg) saturate(6) contrast(2)';
      }
    }
  }, 120);

  var hue = 0;
  setInterval(function(){
    hue = (hue + 37) % 360;
    document.body.style.setProperty('filter', 'hue-rotate(' + hue + 'deg) saturate(3)');
  }, 90);

  window.addEventListener('mousemove', function(e) {
    [1, .9, .8, .5, .1].forEach(function(i) {
      var j = (1 - i) * 50;
      var elem = document.createElement('div');
      var size = Math.ceil(Math.random() * 60 * i) + 'px';
      elem.style.position = 'fixed';
      elem.style.top = e.pageY + Math.round(Math.random() * j - j / 2) + 'px';
      elem.style.left = e.pageX + Math.round(Math.random() * j - j / 2) + 'px';
      elem.style.width = size;
      elem.style.height = size;
      elem.style.background = 'hsla(' +
          Math.round(Math.random() * 360) + ', ' +
          '100%, ' +
          '50%, ' +
          i + ')';
      elem.style.borderRadius = size;
      elem.style.pointerEvents = 'none';
      document.body.appendChild(elem);
      window.setTimeout(function() {
          document.body.removeChild(elem);
      }, Math.round(Math.random() * i * 500));
    });
  }, false);
}

button.addEventListener('click', function() {
    logo.style.display = 'none';
    button.style.display = 'none';
    startChaos();
});




//coppied code monke lazy




//coppied code two monke lazy again
