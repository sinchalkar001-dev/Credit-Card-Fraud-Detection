// Upload page: drag and drop, a summary of the chosen file, and the same
// checks the server makes, done before anything is sent.
import { restart } from './motion.js';

const form = document.querySelector('[data-upload-form]');

if (form) {
  const dropzone = form.querySelector('[data-dropzone]');
  const input = dropzone.querySelector('input[type="file"]');
  const chip = form.querySelector('[data-file-chip]');
  const chipName = chip.querySelector('[data-file-name]');
  const chipSize = chip.querySelector('[data-file-size]');
  const remove = chip.querySelector('[data-file-remove]');
  const error = form.querySelector('[data-upload-error]');
  const errorText = error.querySelector('[data-upload-error-text]');

  const maxBytes = Number(form.dataset.maxBytes);
  const maxMegabytes = form.dataset.maxMegabytes;

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} bytes`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // The wording matches the server's, so a problem reads the same either way.
  const problemWith = (file) => {
    if (!file) return 'Choose a CSV file to score.';
    if (!/\.csv$/i.test(file.name)) return 'Only CSV files can be scored. Export the sheet as .csv and upload it again.';
    if (file.size === 0) return 'The file is empty. Choose a CSV with a header row and at least one row of data.';
    if (file.size > maxBytes) return `The file is larger than ${maxMegabytes} MB. Split it into smaller files and upload each one.`;
    return '';
  };

  const showError = (message) => {
    errorText.textContent = message;
    error.hidden = !message;
    if (message) {
      input.setAttribute('aria-invalid', 'true');
    } else {
      input.removeAttribute('aria-invalid');
    }
  };

  const showFile = () => {
    const file = input.files[0];
    if (!file) {
      chip.hidden = true;
      return;
    }
    chipName.textContent = file.name;
    chipSize.textContent = formatSize(file.size);
    chip.hidden = false;
    restart(chip, 'is-arriving');
    showError(problemWith(file));
  };

  input.addEventListener('change', showFile);

  remove.addEventListener('click', () => {
    input.value = '';
    chip.hidden = true;
    showError('');
    input.focus();
  });

  // Dragging. The file input covers the zone, so a drop lands on it natively;
  // these handlers only add the visual state.
  let depth = 0;
  dropzone.addEventListener('dragenter', () => {
    depth += 1;
    dropzone.setAttribute('data-dragging', '');
  });
  dropzone.addEventListener('dragleave', () => {
    depth -= 1;
    if (depth <= 0) {
      depth = 0;
      dropzone.removeAttribute('data-dragging');
    }
  });
  dropzone.addEventListener('drop', () => {
    depth = 0;
    dropzone.removeAttribute('data-dragging');
  });

  form.noValidate = true;
  form.addEventListener('submit', (event) => {
    const message = problemWith(input.files[0]);
    if (message) {
      event.preventDefault();
      showError(message);
      input.focus();
    }
  });

  // A file kept by the browser across a reload or Back still shows its chip.
  if (input.files.length) showFile();
}
