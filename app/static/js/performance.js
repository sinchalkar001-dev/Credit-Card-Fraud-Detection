// Performance page: switch every figure between the model in use (weighted
// for the uneven classes) and the same model fitted without weights.
// Numbers roll from the old value to the new one.
import { announce } from './app.js';
import { DURATION, countTo, restart } from './motion.js';

const page = document.querySelector('[data-performance]');
const source = document.getElementById('performance-data');

if (page && source) {
  const evaluations = JSON.parse(source.textContent);
  const names = { weighted: 'the weighted model, which is in use', unweighted: 'the unweighted model' };

  const switcher = page.querySelector('[data-evaluations]');
  const buttons = [...switcher.querySelectorAll('[data-evaluation]')];
  const metrics = [...page.querySelectorAll('[data-metric]')];
  const cells = [...page.querySelectorAll('[data-cell]')];
  const tests = [...page.querySelectorAll('[data-test]')];
  const folds = [...page.querySelectorAll('[data-cv]')];
  const methods = [...page.querySelectorAll('[data-method]')];

  let current = page.dataset.serving;

  // A cell's tint shows its share of its row: good (tn, fp) or bad (fn, tp).
  const rowTotal = (matrix, key) => (key === 'tn' || key === 'fp' ? matrix.tn + matrix.fp : matrix.fn + matrix.tp);

  // Shares read as percentages; ROC AUC stays on its 0-1 scale.
  const figure = (value, cell) => {
    const scale = Number(cell.dataset.scale);
    return `${(value * scale).toFixed(Number(cell.dataset.decimals))}${scale === 100 ? '%' : ''}`;
  };

  const show = (name) => {
    if (name === current || !evaluations[name]) return;
    const from = evaluations[current];
    const to = evaluations[name];
    current = name;

    buttons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.evaluation === name)));

    metrics.forEach((metric) => {
      const key = metric.dataset.metric;
      const scale = Number(metric.dataset.scale);
      countTo(metric, to.test[key] * scale, {
        from: from.test[key] * scale,
        decimals: Number(metric.dataset.decimals),
        duration: DURATION.slower,
      });
    });

    cells.forEach((cell) => {
      const key = cell.dataset.cell;
      const matrix = to.test.confusion_matrix;
      const total = rowTotal(matrix, key);
      cell.style.setProperty('--_share', total ? (matrix[key] / total).toFixed(4) : 0);
      countTo(cell.querySelector('[data-cell-count]'), matrix[key], {
        from: from.test.confusion_matrix[key],
        duration: DURATION.slower,
      });
    });

    tests.forEach((cell) => {
      cell.textContent = figure(to.test[cell.dataset.test], cell);
      restart(cell, 'is-switching');
    });

    folds.forEach((cell) => {
      const fold = to.cross_validation[cell.dataset.cv];
      const spread = (fold.std * Number(cell.dataset.scale)).toFixed(Number(cell.dataset.decimals));
      cell.textContent = `${figure(fold.mean, cell)} ± ${spread}`;
      restart(cell, 'is-switching');
    });

    methods.forEach((method) => {
      method.hidden = method.dataset.method !== name;
      if (!method.hidden) restart(method, 'is-switching');
    });

    announce(`Scores for ${names[name]}. Recall ${(to.test.recall * 100).toFixed(1)} percent, `
      + `accuracy ${(to.test.accuracy * 100).toFixed(1)} percent.`);
  };

  switcher.hidden = false;
  buttons.forEach((button) => button.addEventListener('click', () => show(button.dataset.evaluation)));
}
