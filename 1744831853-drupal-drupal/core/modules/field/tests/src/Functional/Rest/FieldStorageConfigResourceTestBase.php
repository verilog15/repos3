<?php

declare(strict_types=1);

namespace Drupal\Tests\field\Functional\Rest;

use Drupal\field\Entity\FieldStorageConfig;
use Drupal\Tests\rest\Functional\EntityResource\ConfigEntityResourceTestBase;

/**
 * Resource test base for the FieldStorageConfig entity.
 */
abstract class FieldStorageConfigResourceTestBase extends ConfigEntityResourceTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = ['field_ui', 'node'];

  /**
   * {@inheritdoc}
   */
  protected static $entityTypeId = 'field_storage_config';

  /**
   * @var \Drupal\field\FieldConfigStorage
   */
  protected $entity;

  /**
   * {@inheritdoc}
   */
  protected function setUpAuthorization($method) {
    $this->grantPermissionsToTestedRole(['administer node fields']);
  }

  /**
   * {@inheritdoc}
   */
  protected function createEntity() {
    $field_storage = FieldStorageConfig::create([
      'field_name' => 'true_llama',
      'entity_type' => 'node',
      'type' => 'boolean',
    ]);
    $field_storage->save();
    return $field_storage;
  }

  /**
   * {@inheritdoc}
   */
  protected function getExpectedNormalizedEntity() {
    return [
      'cardinality' => 1,
      'custom_storage' => FALSE,
      'dependencies' => [
        'module' => ['node'],
      ],
      'entity_type' => 'node',
      'field_name' => 'true_llama',
      'id' => 'node.true_llama',
      'indexes' => [],
      'langcode' => 'en',
      'locked' => FALSE,
      'module' => 'core',
      'persist_with_no_fields' => FALSE,
      'settings' => [],
      'status' => TRUE,
      'translatable' => TRUE,
      'type' => 'boolean',
      'uuid' => $this->entity->uuid(),
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
        return "The 'administer node fields' permission is required.";

      default:
        return parent::getExpectedUnauthorizedAccessMessage($method);
    }
  }

}
