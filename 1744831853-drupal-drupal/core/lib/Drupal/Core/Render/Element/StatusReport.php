<?php

namespace Drupal\Core\Render\Element;

use Drupal\Core\Render\Attribute\RenderElement;

/**
 * Creates status report page element.
 */
#[RenderElement('status_report')]
class StatusReport extends RenderElementBase {

  /**
   * {@inheritdoc}
   */
  public function getInfo() {
    return [
      '#theme' => 'status_report_grouped',
      '#priorities' => [
        'error',
        'warning',
        'checked',
        'ok',
      ],
      '#pre_render' => [
        [static::class, 'preRenderGroupRequirements'],
      ],
    ];
  }

  /**
   * Render API callback: Groups requirements.
   *
   * This function is assigned as a #pre_render callback.
   */
  public static function preRenderGroupRequirements($element) {
    $severities = static::getSeverities();
    $grouped_requirements = [];
    foreach ($element['#requirements'] as $key => $requirement) {
      $severity = $severities[REQUIREMENT_INFO];
      if (isset($requirement['severity'])) {
        $requirement_severity = (int) $requirement['severity'] === REQUIREMENT_OK ? REQUIREMENT_INFO : (int) $requirement['severity'];
        $severity = $severities[$requirement_severity];
      }
      elseif (defined('MAINTENANCE_MODE') && MAINTENANCE_MODE == 'install') {
        $severity = $severities[REQUIREMENT_OK];
      }

      $grouped_requirements[$severity['status']]['title'] = $severity['title'];
      $grouped_requirements[$severity['status']]['type'] = $severity['status'];
      $grouped_requirements[$severity['status']]['items'][$key] = $requirement;
    }

    // Order the grouped requirements by a set order.
    $order = array_flip($element['#priorities']);
    uksort($grouped_requirements, function ($a, $b) use ($order) {
      return $order[$a] <=> $order[$b];
    });

    $element['#grouped_requirements'] = $grouped_requirements;

    return $element;
  }

  /**
   * Gets the severities.
   *
   * @return array
   *   An associative array of the requirements severities. The keys are the
   *   requirement constants defined in install.inc.
   */
  public static function getSeverities() {
    return [
      REQUIREMENT_INFO => [
        'title' => t('Checked', [], ['context' => 'Examined']),
        'status' => 'checked',
      ],
      REQUIREMENT_OK => [
        'title' => t('OK'),
        'status' => 'ok',
      ],
      REQUIREMENT_WARNING => [
        'title' => t('Warnings found'),
        'status' => 'warning',
      ],
      REQUIREMENT_ERROR => [
        'title' => t('Errors found'),
        'status' => 'error',
      ],
    ];
  }

}
