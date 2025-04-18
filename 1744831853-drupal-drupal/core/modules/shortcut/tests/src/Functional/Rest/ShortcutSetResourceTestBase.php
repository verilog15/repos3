<?php

declare(strict_types=1);

namespace Drupal\Tests\shortcut\Functional\Rest;

use Drupal\shortcut\Entity\ShortcutSet;
use Drupal\Tests\rest\Functional\EntityResource\ConfigEntityResourceTestBase;

/**
 * Resource test base for ShortcutSet entity.
 */
abstract class ShortcutSetResourceTestBase extends ConfigEntityResourceTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = ['shortcut'];

  /**
   * {@inheritdoc}
   */
  protected static $entityTypeId = 'shortcut_set';

  /**
   * {@inheritdoc}
   */
  protected static $patchProtectedFieldNames = [];

  /**
   * The ShortcutSet entity.
   *
   * @var \Drupal\shortcut\ShortcutSetInterface
   */
  protected $entity;

  /**
   * {@inheritdoc}
   */
  protected function setUpAuthorization($method) {
    switch ($method) {
      case 'GET':
        $this->grantPermissionsToTestedRole(['access shortcuts']);
        break;

      case 'POST':
      case 'PATCH':
        $this->grantPermissionsToTestedRole(['access shortcuts', 'customize shortcut links']);
        break;

      case 'DELETE':
        $this->grantPermissionsToTestedRole(['administer shortcuts']);
        break;
    }
  }

  /**
   * {@inheritdoc}
   */
  protected function createEntity() {
    $set = ShortcutSet::create([
      'id' => 'llama-set',
      'label' => 'Llama Set',
    ]);
    $set->save();
    return $set;
  }

  /**
   * {@inheritdoc}
   */
  protected function getExpectedNormalizedEntity() {
    return [
      'id' => 'llama-set',
      'uuid' => $this->entity->uuid(),
      'label' => 'Llama Set',
      'status' => TRUE,
      'langcode' => 'en',
      'dependencies' => [],
    ];
  }

  /**
   * {@inheritdoc}
   */
  protected function getNormalizedPostEntity() {
    // @todo Update in https://www.drupal.org/node/2300677.
    return [];
  }

  /**
   * {@inheritdoc}
   */
  protected function getExpectedUnauthorizedAccessMessage($method) {
    switch ($method) {
      case 'GET':
        return "The 'access shortcuts' permission is required.";

      default:
        return parent::getExpectedUnauthorizedAccessMessage($method);
    }
  }

}
