<?php

namespace Drupal\migrate;

/**
 * Interface for migration messages.
 */
interface MigrateMessageInterface {

  /**
   * Displays a migrate message.
   *
   * @param string $message
   *   The message to display.
   * @param string $type
   *   The type of message, for example: status or warning.
   */
  public function display($message, $type = 'status');

}
