// Results page: filter the rows by verdict and list them a page at a time.
import { formatNumber } from './motion.js';

const PAGE = 50;        // rows added per "Show more"
const STAGGERED = 14;   // rows that follow one another in; the rest arrive together

const results = document.querySelector('[data-results]');

if (results) {
  const rows = [...results.querySelectorAll('[data-row]')];
  const filters = results.querySelector('[data-filters]');
  const status = results.querySelector('[data-results-status]');
  const moreBar = results.querySelector('[data-more-bar]');
  const more = results.querySelector('[data-more]');
  const moreStatus = results.querySelector('[data-more-status]');
  const listedNote = status.textContent.trim();

  let filter = 'all';
  let limit = PAGE;

  const matching = () => rows.filter((row) => filter === 'all' || row.dataset.kind === filter);

  const render = (animateFrom = 0) => {
    const matches = matching();
    const position = new Map(matches.map((row, index) => [row, index]));

    let entering = 0;
    rows.forEach((row) => {
      const show = position.has(row) && position.get(row) < limit;
      const wasHidden = row.hidden;
      row.hidden = !show;
      row.classList.remove('is-entering');

      if (show && wasHidden && position.get(row) >= animateFrom) {
        row.style.setProperty('--i', Math.min(entering, STAGGERED));
        row.classList.add('is-entering');
        entering += 1;
      }
    });

    const shown = Math.min(limit, matches.length);
    moreBar.hidden = shown >= matches.length;
    moreStatus.textContent = `Showing ${formatNumber(shown)} of ${formatNumber(matches.length)} rows`;
    more.textContent = `Show ${formatNumber(Math.min(PAGE, matches.length - shown))} more`;

    const label = { all: 'rows', flagged: 'flagged rows', cleared: 'cleared rows', skipped: 'rows that were not scored' }[filter];
    status.textContent = matches.length
      ? `${formatNumber(matches.length)} ${label}. ${listedNote}`.trim()
      : `No ${label} in this file.`;
  };

  // Count each kind once, for the chips.
  const counts = rows.reduce((totals, row) => {
    totals[row.dataset.kind] = (totals[row.dataset.kind] || 0) + 1;
    return totals;
  }, { all: rows.length });

  filters.querySelectorAll('[data-filter]').forEach((chip) => {
    const count = document.createElement('span');
    count.className = 'chip__count';
    count.textContent = formatNumber(counts[chip.dataset.filter] || 0);
    chip.append(count);
  });

  filters.hidden = false;
  filters.addEventListener('click', (event) => {
    const chip = event.target.closest('[data-filter]');
    if (!chip || chip.dataset.filter === filter) return;

    filter = chip.dataset.filter;
    limit = PAGE;
    filters.querySelectorAll('[data-filter]').forEach((other) => {
      other.setAttribute('aria-pressed', String(other === chip));
    });
    // Start from a clean slate so the new set fades in together.
    rows.forEach((row) => { row.hidden = true; });
    render();
  });

  more.addEventListener('click', () => {
    const from = limit;
    limit += PAGE;
    render(from);
  });

  // First paint: everything beyond the first page is tucked away, without animation.
  rows.forEach((row, index) => { row.hidden = index >= limit; });
  render(rows.length);
}
