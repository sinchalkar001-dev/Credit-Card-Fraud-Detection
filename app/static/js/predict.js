// Check an application: send the form without leaving the page, show any
// problems next to their fields, and play the verdict on the slip.
import { announce } from './app.js';
import { DURATION, reducedMotion, restart, tween, wait } from './motion.js';

const MIN_BUSY = 450;      // long enough to read as a check, short enough not to drag
const SWEEP = 900;         // the needle's travel to the result

const form = document.querySelector('[data-check-form]');
const slip = document.querySelector('[data-slip]');

if (form && slip) {
  const submit = form.querySelector('[type="submit"]');
  const clear = form.querySelector('[data-clear]');
  const summary = form.querySelector('[data-error-summary]');
  const summaryTitle = summary.querySelector('[data-error-title]');
  const summaryList = summary.querySelector('[data-error-list]');

  const gauge = slip.querySelector('[data-gauge]');
  const number = slip.querySelector('[data-gauge-number]');
  const stamp = slip.querySelector('[data-stamp]');
  const title = slip.querySelector('[data-slip-title]');
  const text = slip.querySelector('[data-slip-text]');
  const problem = slip.querySelector('[data-slip-problem]');
  const problemText = slip.querySelector('[data-slip-problem-text]');

  let stopSweep = () => {};

  // --- The slip -------------------------------------------------------------

  // Never round a near-certain score up to a flat 100 or down to a flat 0.
  const formatScore = (value) => {
    if (value > 0 && value < 0.1) return '<0.1';
    if (value < 100 && value > 99.9) return '>99.9';
    return value.toFixed(1);
  };

  const setGauge = (value) => {
    gauge.style.setProperty('--_value', (value / 100).toFixed(4));
    number.textContent = formatScore(value);
  };

  const setMessage = (heading, body) => {
    title.textContent = heading;
    text.textContent = body;
  };

  const resetSlip = () => {
    stopSweep();
    slip.dataset.state = 'idle';
    slip.removeAttribute('data-verdict');
    slip.classList.remove('is-stamping', 'is-settling');
    problem.hidden = true;
    setGauge(0);
    number.textContent = '0';
    setMessage('No verdict yet', 'Fill in the form, then choose Check application.');
  };

  const showProblem = (message) => {
    resetSlip();
    problemText.textContent = message;
    problem.hidden = false;
    setMessage('The check did not finish', 'Nothing was scored.');
  };

  const showResult = (result) => {
    const score = result.risk_score;
    const flagged = result.flagged;

    stopSweep();
    problem.hidden = true;
    slip.dataset.state = 'sweeping';
    slip.dataset.verdict = flagged ? 'flagged' : 'cleared';
    slip.classList.remove('is-stamping', 'is-settling');
    stamp.textContent = flagged ? 'Flagged' : 'Cleared';
    stamp.classList.toggle('stamp--risk', flagged);

    const heading = flagged ? 'Flagged as high risk' : 'Looks low risk';
    const body = `The model scores this application ${formatScore(score)} out of 100, `
      + `${flagged ? 'over' : 'under'} its line of 50.`;

    // The needle travels to the score; the stamp lands once it has arrived.
    stopSweep = tween({
      from: 0,
      to: score,
      duration: SWEEP,
      onUpdate: setGauge,
      onDone: () => {
        slip.dataset.state = 'result';
        setMessage(heading, body);
        if (!reducedMotion()) {
          restart(slip, 'is-stamping');
          slip.classList.add('is-settling');
        }
        announce(`${heading}. Risk score ${formatScore(score)} out of 100.`);
      },
    });

    // On a narrow screen the slip sits under the form: bring it into view.
    const box = slip.getBoundingClientRect();
    if (box.top < 0 || box.bottom > window.innerHeight) {
      slip.scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth', block: 'center' });
    }
  };

  const setBusy = (busy) => {
    if (!busy) {
      submit.removeAttribute('aria-busy');
      return;
    }
    submit.setAttribute('aria-busy', 'true');
    stopSweep();
    slip.dataset.state = 'busy';
    slip.classList.remove('is-stamping', 'is-settling');
    problem.hidden = true;
    setMessage('Checking', 'The model is reading the twenty details.');
  };

  // --- Field errors ------------------------------------------------------------

  const fieldFor = (name) => form.querySelector(`[data-field="${name}"]`);
  const controlsIn = (field) => field.querySelectorAll('input, select');
  // The element that carries aria-invalid: the control itself, or the segmented group.
  const invalidTarget = (field) => field.querySelector('.segmented') || field.querySelector('input, select');

  const clearFieldError = (field) => {
    const error = field.querySelector('.field__error');
    if (error.hidden) return;
    error.hidden = true;
    error.querySelector('[data-error-text]').textContent = '';
    invalidTarget(field).removeAttribute('aria-invalid');
  };

  const refreshSummary = () => {
    const open = [...form.querySelectorAll('.field__error:not([hidden])')];
    if (!open.length) {
      summary.hidden = true;
      summaryList.replaceChildren();
      return;
    }

    summaryTitle.textContent = `Fix ${open.length} ${open.length === 1 ? 'field' : 'fields'} to get a verdict`;
    summaryList.replaceChildren(...open.map((error) => {
      const field = error.closest('[data-field]');
      const link = document.createElement('a');
      link.href = `#field-${field.dataset.field}`;
      link.textContent = error.querySelector('[data-error-text]').textContent;
      const item = document.createElement('li');
      item.append(link);
      return item;
    }));
    summary.hidden = false;
  };

  const showErrors = (errors) => {
    Object.entries(errors).forEach(([name, message]) => {
      const field = fieldFor(name);
      if (!field) return;
      const error = field.querySelector('.field__error');
      error.querySelector('[data-error-text]').textContent = message;
      error.hidden = false;
      invalidTarget(field).setAttribute('aria-invalid', 'true');
    });

    refreshSummary();
    resetSlip();
    setMessage('No verdict yet', 'Some details still need fixing.');
    summary.focus();
  };

  // A link in the summary goes to its field and puts the cursor in it.
  summaryList.addEventListener('click', (event) => {
    const link = event.target.closest('a');
    if (!link) return;
    event.preventDefault();
    const control = form.querySelector(link.getAttribute('href'));
    if (!control) return;
    control.focus({ preventScroll: true });
    control.scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth', block: 'center' });
  });

  // An error goes away as soon as its field has a usable value again.
  form.querySelectorAll('[data-field]').forEach((field) => {
    const settle = () => {
      const controls = [...controlsIn(field)];
      if (controls.every((control) => control.validity.valid)) {
        clearFieldError(field);
        refreshSummary();
      }
    };
    field.addEventListener('change', settle);
    field.addEventListener('input', settle);
  });

  // --- Sending the form --------------------------------------------------------

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submit.getAttribute('aria-busy') === 'true') return;

    setBusy(true);
    const started = performance.now();
    let response;
    let body;

    try {
      response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { Accept: 'application/json' },
      });
      // A signed-out session answers with the sign-in page instead of JSON.
      if (response.redirected) {
        window.location.assign(response.url);
        return;
      }
      body = await response.json();
    } catch (error) {
      setBusy(false);
      showProblem('The check could not reach the server. Make sure the app is still running, then try again.');
      return;
    }

    await wait(Math.max(0, MIN_BUSY - (performance.now() - started)));
    setBusy(false);

    if (body.ok) {
      showResult(body.result);
    } else if (body.errors) {
      showErrors(body.errors);
    } else {
      showProblem(body.message || body.detail || 'The check could not be completed. Try again.');
    }
  });

  // --- Examples and clearing ---------------------------------------------------

  const fill = (values) => {
    Object.entries(values).forEach(([name, value]) => {
      const field = fieldFor(name);
      if (!field) return;

      const radios = field.querySelectorAll('input[type="radio"]');
      if (radios.length) {
        radios.forEach((radio) => { radio.checked = radio.value === String(value); });
      } else {
        field.querySelector('input, select').value = String(value);
      }

      clearFieldError(field);
      // Light up what changed, so the eye can follow the fill.
      const lit = field.querySelector('.segmented') || field;
      restart(lit, 'is-filled');
      window.setTimeout(() => lit.classList.remove('is-filled'), DURATION.slower + 100);
    });
    refreshSummary();
    resetSlip();
  };

  const examples = document.querySelector('[data-examples]');
  if (examples) {
    examples.hidden = false;
    examples.addEventListener('click', (event) => {
      const button = event.target.closest('[data-example]');
      if (!button) return;
      fill(JSON.parse(button.dataset.example));
      announce(`${button.textContent.trim()} loaded. Choose Check application to score it.`);
    });
  }

  if (clear) {
    clear.hidden = false;
    form.addEventListener('reset', () => {
      form.querySelectorAll('[data-field]').forEach(clearFieldError);
      refreshSummary();
      resetSlip();
    });
  }

  // The browser's own bubbles would duplicate the messages shown in the page.
  form.noValidate = true;

  // A verdict rendered by the server (no script on the previous request) is
  // played back the same way as a fresh one.
  if (slip.hasAttribute('data-autoplay')) {
    const score = Number(slip.dataset.score);
    slip.removeAttribute('data-autoplay');
    showResult({ risk_score: score, flagged: slip.dataset.verdict === 'flagged' });
  }
}
