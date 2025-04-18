<?php

/**
 * @file
 * Batch processing API for processes to run in multiple HTTP requests.
 *
 * Note that batches are usually invoked by form submissions, which is
 * why the core interaction functions of the batch processing API live in
 * form.inc.
 *
 * @see form.inc
 * @see batch_set()
 * @see batch_process()
 * @see batch_get()
 */

use Drupal\Component\Utility\Timer;
use Drupal\Component\Utility\UrlHelper;
use Drupal\Core\Batch\Percentage;
use Drupal\Core\Form\FormState;
use Drupal\Core\Url;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\RedirectResponse;
use Symfony\Component\HttpKernel\Exception\NotFoundHttpException;

/**
 * Renders the batch processing page based on the current state of the batch.
 *
 * @param \Symfony\Component\HttpFoundation\Request $request
 *   The current request object.
 *
 * @see _batch_shutdown()
 */
function _batch_page(Request $request) {
  $batch = &batch_get();

  if (!($request_id = $request->query->get('id'))) {
    return FALSE;
  }

  // Retrieve the current state of the batch.
  if (!$batch) {
    $batch = \Drupal::service('batch.storage')->load($request_id);
    if (!$batch) {
      \Drupal::messenger()->addError(t('No batch with ID @batch exists.', ['@batch' => $request_id]));
      throw new NotFoundHttpException(sprintf('No batch with ID %s exists.', $request_id));
    }
  }

  // We need to store the updated batch information in the batch storage after
  // processing the batch. In order for the error page to work correctly this
  // needs to be done even in case of a PHP fatal error in which case the end of
  // this function is never reached. Therefore we register a shutdown function
  // to handle this case. Because with FastCGI and fastcgi_finish_request()
  // shutdown functions are called after the HTTP connection is closed, updating
  // the batch information in a shutdown function would lead to race conditions
  // between consecutive requests if the batch processing continues. In case of
  // a fatal error the processing stops anyway, so it works even with FastCGI.
  // However, we must ensure to only update in the shutdown phase in this
  // particular case we track whether the batch information still needs to be
  // updated.
  // @see _batch_shutdown()
  // @see \Symfony\Component\HttpFoundation\Response::send()
  drupal_register_shutdown_function('_batch_shutdown');
  _batch_needs_update(TRUE);

  $build = [];

  // Add batch-specific libraries.
  foreach ($batch['sets'] as $batch_set) {
    if (isset($batch_set['library'])) {
      foreach ($batch_set['library'] as $library) {
        $build['#attached']['library'][] = $library;
      }
    }
  }

  $response = FALSE;
  $op = $request->query->get('op', '');
  switch ($op) {
    case 'start':
    case 'do_nojs':
      // Display the full progress page on startup and on each additional
      // non-JavaScript iteration.
      $current_set = _batch_current_set();
      $build['#title'] = $current_set['title'];
      $build['content'] = _batch_progress_page();

      $response = $build;
      break;

    case 'do':
      // JavaScript-based progress page callback.
      $response = _batch_do();
      break;

    case 'finished':
      // _batch_finished() returns a RedirectResponse.
      $response = _batch_finished();
      break;
  }

  if ($batch) {
    \Drupal::service('batch.storage')->update($batch);
  }
  _batch_needs_update(FALSE);

  return $response;
}

/**
 * Checks whether the batch information needs to be updated in the storage.
 *
 * @param bool $new_value
 *   (optional) A new value to set.
 *
 * @return bool
 *   TRUE if the batch information needs to be updated; FALSE otherwise.
 */
function _batch_needs_update($new_value = NULL) {
  $needs_update = &drupal_static(__FUNCTION__, FALSE);

  if (isset($new_value)) {
    $needs_update = $new_value;
  }

  return $needs_update;
}

/**
 * Does one execution pass with JavaScript and returns progress to the browser.
 *
 * @see _batch_progress_page_js()
 * @see _batch_process()
 */
function _batch_do() {
  // Perform actual processing.
  [$percentage, $message, $label] = _batch_process();

  return new JsonResponse(['status' => TRUE, 'percentage' => $percentage, 'message' => $message, 'label' => $label]);
}

/**
 * Outputs a batch processing page.
 *
 * @see _batch_process()
 */
function _batch_progress_page(): array {
  $batch = &batch_get();

  $current_set = _batch_current_set();

  $new_op = 'do_nojs';

  if (!isset($batch['running'])) {
    // This is the first page so we return some output immediately.
    $percentage       = 0;
    $message          = $current_set['init_message'];
    $label            = '';
    $batch['running'] = TRUE;
  }
  else {
    // This is one of the later requests; do some processing first.

    // Error handling: if PHP dies due to a fatal error (e.g. a nonexistent
    // function), it will output whatever is in the output buffer, followed by
    // the error message.
    ob_start();
    $fallback = $current_set['error_message'] . '<br />' . $batch['error_message'];

    // We strip the end of the page using a marker in the template, so any
    // additional HTML output by PHP shows up inside the page rather than below
    // it. While this causes invalid HTML, the same would be true if we didn't,
    // as content is not allowed to appear after </html> anyway.
    $bare_html_page_renderer = \Drupal::service('bare_html_page_renderer');
    $response = $bare_html_page_renderer->renderBarePage(['#markup' => $fallback], $current_set['title'], 'maintenance_page', [
      '#show_messages' => FALSE,
    ]);

    // Just use the content of the response.
    $fallback = $response->getContent();

    [$fallback] = explode('<!--partial-->', $fallback);
    print $fallback;

    // Perform actual processing.
    [$percentage, $message, $label] = _batch_process();
    if ($percentage == 100) {
      $new_op = 'finished';
    }

    // PHP did not die; remove the fallback output.
    ob_end_clean();
  }

  // Merge required query parameters for batch processing into those provided by
  // batch_set() or hook_batch_alter().
  $query_options = $batch['url']->getOption('query');
  $query_options['id'] = $batch['id'];
  $query_options['op'] = $new_op;
  $batch['url']->setOption('query', $query_options);

  $url = $batch['url']->toString(TRUE)->getGeneratedUrl();

  $build = [
    '#theme' => 'progress_bar',
    '#percent' => $percentage,
    '#message' => ['#markup' => $message],
    '#label' => $label,
    '#attached' => [
      'html_head' => [
        [
          [
            // Redirect through a 'Refresh' meta tag if JavaScript is disabled.
            '#tag' => 'meta',
            '#noscript' => TRUE,
            '#attributes' => [
              'http-equiv' => 'Refresh',
              'content' => '0; URL=' . $url,
            ],
          ],
          'batch_progress_meta_refresh',
        ],
      ],
      // Adds JavaScript code and settings for clients where JavaScript is
      // enabled.
      'drupalSettings' => [
        'batch' => [
          'errorMessage' => $current_set['error_message'] . '<br />' . $batch['error_message'],
          'initMessage' => $current_set['init_message'],
          'uri' => $url,
        ],
      ],
      'library' => [
        'core/drupal.batch',
      ],
    ],
  ];
  return $build;
}

/**
 * Processes sets in a batch.
 *
 * If the batch was marked for progressive execution (default), this executes as
 * many operations in batch sets until an execution time of 1 second has been
 * exceeded. It will continue with the next operation of the same batch set in
 * the next request.
 *
 * @return array
 *   An array containing a completion value (in percent) and a status message.
 */
function _batch_process() {
  $batch       = &batch_get();
  $current_set = &_batch_current_set();
  // Indicate that this batch set needs to be initialized.
  $set_changed = TRUE;
  $task_message = '';

  // If this batch was marked for progressive execution (e.g. forms submitted by
  // \Drupal::formBuilder()->submitForm(), initialize a timer to determine
  // whether we need to proceed with the same batch phase when a processing time
  // of 1 second has been exceeded.
  if ($batch['progressive']) {
    Timer::start('batch_processing');
  }

  if (empty($current_set['start'])) {
    $current_set['start'] = microtime(TRUE);
  }

  $queue = _batch_queue($current_set);

  while (!$current_set['success']) {
    // If this is the first time we iterate this batch set in the current
    // request, we check if it requires an additional file for functions
    // definitions.
    if ($set_changed && isset($current_set['file']) && is_file($current_set['file'])) {
      include_once \Drupal::root() . '/' . $current_set['file'];
    }

    $task_message = '';
    // Assume a single pass operation and set the completion level to 1 by
    // default.
    $finished = 1;

    if ($item = $queue->claimItem()) {
      [$callback, $args] = $item->data;

      // Build the 'context' array and execute the function call.
      $batch_context = [
        'sandbox'  => &$current_set['sandbox'],
        'results'  => &$current_set['results'],
        'finished' => &$finished,
        'message'  => &$task_message,
      ];
      call_user_func_array($callback, array_merge($args, [&$batch_context]));

      if ($finished >= 1) {
        // Make sure this step is not counted twice when computing $current.
        $finished = 0;
        // Remove the processed operation and clear the sandbox.
        $queue->deleteItem($item);
        $current_set['count']--;
        $current_set['sandbox'] = [];
      }
    }

    // When all operations in the current batch set are completed, browse
    // through the remaining sets, marking them 'successfully processed'
    // along the way, until we find a set that contains operations.
    // _batch_next_set() executes form submit handlers stored in 'control'
    // sets (see \Drupal::service('form_submitter')), which can in turn add new
    // sets to the batch.
    $set_changed = FALSE;
    $old_set = $current_set;
    while (empty($current_set['count']) && ($current_set['success'] = TRUE) && _batch_next_set()) {
      $current_set = &_batch_current_set();
      $current_set['start'] = microtime(TRUE);
      $set_changed = TRUE;
    }

    // At this point, either $current_set contains operations that need to be
    // processed or all sets have been completed.
    $queue = _batch_queue($current_set);

    // If we are in progressive mode, break processing after 1 second.
    if ($batch['progressive'] && Timer::read('batch_processing') > 1000) {
      // Record elapsed wall clock time.
      $current_set['elapsed'] = round((microtime(TRUE) - $current_set['start']) * 1000, 2);
      break;
    }
  }

  if ($batch['progressive']) {
    // Gather progress information.

    // Reporting 100% progress will cause the whole batch to be considered
    // processed. If processing was paused right after moving to a new set,
    // we have to use the info from the new (unprocessed) set.
    if ($set_changed && isset($current_set['queue'])) {
      // Processing will continue with a fresh batch set.
      $remaining        = $current_set['count'];
      $total            = $current_set['total'];
      $progress_message = $current_set['init_message'];
      $task_message     = '';
    }
    else {
      // Processing will continue with the current batch set.
      $remaining        = $old_set['count'] ?? 0;
      $total            = $old_set['total'] ?? 0;
      $progress_message = $old_set['progress_message'] ?? '';
    }

    // Total progress is the number of operations that have fully run plus the
    // completion level of the current operation.
    $current    = $total - $remaining + ($finished ?? 0);
    $percentage = _batch_api_percentage($total, $current);
    $elapsed    = $current_set['elapsed'] ?? 0;
    $values     = [
      '@remaining'  => $remaining,
      '@total'      => $total,
      '@current'    => floor($current),
      '@percentage' => $percentage,
      '@elapsed'    => \Drupal::service('date.formatter')->formatInterval((int) ($elapsed / 1000)),
      // If possible, estimate remaining processing time.
      '@estimate'   => ($current > 0) ? \Drupal::service('date.formatter')->formatInterval((int) (($elapsed * ($total - $current) / $current) / 1000)) : '-',
    ];
    $message    = strtr($progress_message, $values);

    return [$percentage, $message, $task_message];
  }
  else {
    // If we are not in progressive mode, the entire batch has been processed.
    return _batch_finished();
  }
}

/**
 * Formats the percent completion for a batch set.
 *
 * @param int $total
 *   The total number of operations.
 * @param int|float $current
 *   The number of the current operation. This may be a floating point number
 *   rather than an integer in the case of a multi-step operation that is not
 *   yet complete; in that case, the fractional part of $current represents the
 *   fraction of the operation that has been completed.
 *
 * @return string
 *   The properly formatted percentage, as a string. We output percentages
 *   using the correct number of decimal places so that we never print "100%"
 *   until we are finished, but we also never print more decimal places than
 *   are meaningful.
 *
 * @see _batch_process()
 */
function _batch_api_percentage($total, $current) {
  return Percentage::format($total, $current);
}

/**
 * Returns the batch set being currently processed.
 */
function &_batch_current_set() {
  $batch = &batch_get();
  return $batch['sets'][$batch['current_set']];
}

/**
 * Retrieves the next set in a batch.
 *
 * If there is a subsequent set in this batch, assign it as the new set to
 * process and execute its form submit handler (if defined), which may add
 * further sets to this batch.
 *
 * @return true|null
 *   TRUE if a subsequent set was found in the batch; no value will be returned
 *   if no subsequent set was found.
 */
function _batch_next_set() {
  $batch = &batch_get();
  $set_indexes = array_keys($batch['sets']);
  $current_set_index_key = array_search($batch['current_set'], $set_indexes);
  if (isset($set_indexes[$current_set_index_key + 1])) {
    $batch['current_set'] = $set_indexes[$current_set_index_key + 1];
    $current_set = &_batch_current_set();
    if (isset($current_set['form_submit']) && ($callback = $current_set['form_submit']) && is_callable($callback)) {
      // We use our stored copies of $form and $form_state to account for
      // possible alterations by previous form submit handlers.
      $complete_form = &$batch['form_state']->getCompleteForm();
      call_user_func_array($callback, [&$complete_form, &$batch['form_state']]);
    }
    return TRUE;
  }
}

/**
 * Ends the batch processing.
 *
 * Call the 'finished' callback of each batch set to allow custom handling of
 * the results and resolve page redirection.
 */
function _batch_finished() {
  $batch = &batch_get();
  $batch_finished_redirect = NULL;

  // Execute the 'finished' callbacks for each batch set, if defined.
  foreach ($batch['sets'] as $batch_set) {
    if (isset($batch_set['finished'])) {
      // Check if the set requires an additional file for function definitions.
      if (isset($batch_set['file']) && is_file($batch_set['file'])) {
        include_once \Drupal::root() . '/' . $batch_set['file'];
      }
      if (is_callable($batch_set['finished'])) {
        $queue = _batch_queue($batch_set);
        $operations = $queue->getAllItems();
        $batch_set_result = call_user_func_array($batch_set['finished'], [$batch_set['success'], $batch_set['results'], $operations, \Drupal::service('date.formatter')->formatInterval((int) ($batch_set['elapsed'] / 1000))]);
        // If a batch 'finished' callback requested a redirect after the batch
        // is complete, save that for later use. If more than one batch set
        // returned a redirect, the last one is used.
        if ($batch_set_result instanceof RedirectResponse) {
          $batch_finished_redirect = $batch_set_result;
        }
      }
    }
  }

  // Clean up the batch table and unset the static $batch variable.
  if ($batch['progressive']) {
    \Drupal::service('batch.storage')->delete($batch['id']);
    foreach ($batch['sets'] as $batch_set) {
      if ($queue = _batch_queue($batch_set)) {
        $queue->deleteQueue();
      }
    }
    // Clean-up the session. Not needed for CLI updates.
    $session = \Drupal::request()->getSession();
    $batches = $session->get('batches', []);
    unset($batches[$batch['id']]);
    if (empty($batches)) {
      $session->remove('batches');
    }
    else {
      $session->set('batches', $batches);
    }
  }
  $_batch = $batch;
  $batch = NULL;

  // Redirect if needed.
  if ($_batch['progressive']) {
    // Revert the 'destination' that was saved in batch_process().
    if (isset($_batch['destination'])) {
      \Drupal::request()->query->set('destination', $_batch['destination']);
    }

    // Determine the target path to redirect to. If a batch 'finished' callback
    // returned a redirect response object, use that. Otherwise, fall back on
    // the form redirection.
    if (isset($batch_finished_redirect)) {
      return $batch_finished_redirect;
    }
    elseif (!isset($_batch['form_state'])) {
      $_batch['form_state'] = new FormState();
    }
    if ($_batch['form_state']->getRedirect() === NULL) {
      $redirect = $_batch['batch_redirect'] ?: $_batch['source_url'];
      // Any path with a scheme does not correspond to a route.
      if (!$redirect instanceof Url) {
        $options = UrlHelper::parse($redirect);
        if (parse_url($options['path'], PHP_URL_SCHEME)) {
          $redirect = Url::fromUri($options['path'], $options);
        }
        else {
          $redirect = \Drupal::pathValidator()->getUrlIfValid($options['path']);
          if (!$redirect) {
            // Stay on the same page if the redirect was invalid.
            $redirect = Url::fromRoute('<current>');
          }
          $redirect->setOptions($options);
        }
      }
      $_batch['form_state']->setRedirectUrl($redirect);
    }

    // Use \Drupal\Core\Form\FormSubmitterInterface::redirectForm() to handle
    // the redirection logic.
    $redirect = \Drupal::service('form_submitter')->redirectForm($_batch['form_state']);
    if (is_object($redirect)) {
      return $redirect;
    }

    // If no redirection happened, redirect to the originating page. In case the
    // form needs to be rebuilt, save the final $form_state for
    // \Drupal\Core\Form\FormBuilderInterface::buildForm().
    if ($_batch['form_state']->isRebuilding()) {
      $session = \Drupal::request()->getSession();
      $session->set('batch_form_state', $_batch['form_state']);
    }
    $callback = $_batch['redirect_callback'];
    $_batch['source_url']->mergeOptions(['query' => ['op' => 'finish', 'id' => $_batch['id']]]);
    if (is_callable($callback)) {
      $callback($_batch['source_url'], $_batch['source_url']->getOption('query'));
    }
    elseif ($callback === NULL) {
      // Default to RedirectResponse objects when nothing specified.
      return new RedirectResponse($_batch['source_url']->setAbsolute()->toString());
    }
  }
}

/**
 * Shutdown function: Stores the current batch data for the next request.
 *
 * @see _batch_page()
 * @see drupal_register_shutdown_function()
 */
function _batch_shutdown(): void {
  if (($batch = batch_get()) && _batch_needs_update()) {
    \Drupal::service('batch.storage')->update($batch);
  }
}
