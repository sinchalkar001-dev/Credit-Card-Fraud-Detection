// Home page: play the inspection sequence once. The timing lives in
// css/motion.css; this only starts it and marks it finished.
import { reducedMotion } from './motion.js';

const SEQUENCE_LENGTH = 3000;  // the last step of the sequence ends just before this

const scene = document.querySelector('[data-inspection]');

if (scene) {
  if (reducedMotion()) {
    scene.classList.add('is-done');
  } else {
    scene.classList.add('is-playing');
    window.setTimeout(() => scene.classList.replace('is-playing', 'is-done'), SEQUENCE_LENGTH);
  }
}
