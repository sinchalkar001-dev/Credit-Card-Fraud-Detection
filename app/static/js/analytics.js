// Analytics page: regroup the bad-rate chart by any model input, switch
// between chart and table, and show a detail tooltip on each bar.
import { announce } from './app.js';
import { formatNumber, nextFrame, restart } from './motion.js';

const breakdown = document.querySelector('[data-breakdown]');
const source = document.getElementById('analytics-data');

if (breakdown && source) {
  const { domain, dimensions } = JSON.parse(source.textContent);
  const byName = new Map(dimensions.map((dimension) => [dimension.name, dimension]));

  const toolbar = breakdown.querySelector('[data-chart-toolbar]');
  const select = breakdown.querySelector('[data-dimension]');
  const heading = breakdown.querySelector('[data-dimension-name]');
  const bars = breakdown.querySelector('[data-bars]');
  const tableHead = breakdown.querySelector('[data-table-dimension]');
  const tableBody = breakdown.querySelector('[data-table-rows]');

  const percent = (rate, decimals = 0) => `${(rate * 100).toFixed(decimals)}%`;
  const records = (count) => `${formatNumber(count)} ${count === 1 ? 'record' : 'records'}`;

  // Group names come from the dataset, so they go in as text, never as markup.
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const barRow = (row, index) => {
    const node = element('div', 'bars__row');
    node.tabIndex = 0;
    node.style.setProperty('--i', index);
    node.dataset.tipTitle = `${percent(row.rate, 1)} bad`;
    node.dataset.tipText = `${formatNumber(row.bad)} of ${records(row.total)}`;

    const label = element('span', 'bars__label', row.label);
    label.append(element('small', '', records(row.total)));

    const bar = element('span', 'bars__bar');
    bar.dataset.grow = '';
    bar.style.setProperty('--value', (row.rate / domain).toFixed(4));
    bar.style.setProperty('--_grow', 0);  // starts at the baseline, released below

    const plot = element('span', 'bars__plot');
    plot.append(bar, element('span', 'bars__value', percent(row.rate)));

    node.append(label, plot);
    return node;
  };

  const tableRow = (row) => {
    const node = element('tr');
    const name = element('th', '', row.label);
    name.scope = 'row';
    node.append(
      name,
      element('td', 'is-number', formatNumber(row.total)),
      element('td', 'is-number', formatNumber(row.bad)),
      element('td', 'is-number', percent(row.rate, 1)),
    );
    return node;
  };

  const show = (name) => {
    const dimension = byName.get(name);
    if (!dimension) return;

    heading.textContent = dimension.label.toLowerCase();
    tableHead.textContent = dimension.label;
    bars.replaceChildren(...dimension.rows.map(barRow));
    tableBody.replaceChildren(...dimension.rows.map(tableRow));

    // Let the bars paint at zero, then let them grow to their values.
    nextFrame().then(() => {
      bars.querySelectorAll('.bars__bar').forEach((bar) => bar.style.removeProperty('--_grow'));
    });
    announce(`Bad rate by ${dimension.label.toLowerCase()}, ${dimension.rows.length} groups.`);
  };

  toolbar.hidden = false;
  select.addEventListener('change', () => show(select.value));

  // --- Chart or table ---------------------------------------------------------
  const panels = [...breakdown.querySelectorAll('[data-view-panel]')];
  const views = [...breakdown.querySelectorAll('[data-view]')];

  views.forEach((button) => {
    button.addEventListener('click', () => {
      views.forEach((other) => other.setAttribute('aria-pressed', String(other === button)));
      panels.forEach((panel) => {
        panel.hidden = panel.dataset.viewPanel !== button.dataset.view;
        if (!panel.hidden) restart(panel, 'is-switching');
      });
    });
  });

  // --- Tooltip ----------------------------------------------------------------
  const tooltip = element('div', 'tooltip');
  tooltip.setAttribute('role', 'tooltip');
  const tipTitle = element('strong');
  const tipText = element('span');
  tooltip.append(tipTitle, tipText);
  document.body.append(tooltip);

  const place = (x, y) => {
    const box = tooltip.getBoundingClientRect();
    const left = Math.min(Math.max(8, x + 14), window.innerWidth - box.width - 8);
    const top = y - box.height - 12 < 8 ? y + 18 : y - box.height - 12;
    tooltip.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`;
  };

  const open = (row, x, y) => {
    tipTitle.textContent = row.dataset.tipTitle;
    tipText.textContent = row.dataset.tipText;
    tooltip.setAttribute('data-visible', '');
    place(x, y);
  };

  const close = () => tooltip.removeAttribute('data-visible');

  bars.addEventListener('pointermove', (event) => {
    const row = event.target.closest('.bars__row');
    if (row) open(row, event.clientX, event.clientY);
    else close();
  });
  bars.addEventListener('pointerleave', close);

  // The same detail on keyboard focus, anchored to the end of the bar.
  bars.addEventListener('focusin', (event) => {
    const row = event.target.closest('.bars__row');
    if (!row) return;
    const anchor = row.querySelector('.bars__value').getBoundingClientRect();
    open(row, anchor.right, anchor.top);
  });
  bars.addEventListener('focusout', close);
  window.addEventListener('scroll', close, { passive: true });
}
