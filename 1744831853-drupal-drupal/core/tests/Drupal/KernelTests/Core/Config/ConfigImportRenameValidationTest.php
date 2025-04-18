<?php

declare(strict_types=1);

namespace Drupal\KernelTests\Core\Config;

use Drupal\Component\Uuid\Php;
use Drupal\Core\Config\ConfigImporter;
use Drupal\Core\Config\ConfigImporterException;
use Drupal\Core\Config\StorageComparer;
use Drupal\node\Entity\NodeType;
use Drupal\KernelTests\KernelTestBase;

/**
 * Tests validating renamed configuration in a configuration import.
 *
 * @group config
 */
class ConfigImportRenameValidationTest extends KernelTestBase {

  /**
   * Config Importer object used for testing.
   *
   * @var \Drupal\Core\Config\ConfigImporter
   */
  protected $configImporter;

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'system',
    'user',
    'node',
    'field',
    'text',
    'config_test',
  ];

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();

    $this->installEntitySchema('user');
    $this->installEntitySchema('node');
    $this->installConfig(['system', 'field']);

    // Set up the ConfigImporter object for testing.
    $storage_comparer = new StorageComparer(
      $this->container->get('config.storage.sync'),
      $this->container->get('config.storage')
    );
    $this->configImporter = new ConfigImporter(
      $storage_comparer->createChangelist(),
      $this->container->get('event_dispatcher'),
      $this->container->get('config.manager'),
      $this->container->get('lock.persistent'),
      $this->container->get('config.typed'),
      $this->container->get('module_handler'),
      $this->container->get('module_installer'),
      $this->container->get('theme_handler'),
      $this->container->get('string_translation'),
      $this->container->get('extension.list.module'),
      $this->container->get('extension.list.theme')
    );
  }

  /**
   * Tests configuration renaming validation.
   */
  public function testRenameValidation(): void {
    // Create a test entity.
    $test_entity_id = $this->randomMachineName();
    $test_entity = \Drupal::entityTypeManager()->getStorage('config_test')->create([
      'id' => $test_entity_id,
      'label' => $this->randomMachineName(),
    ]);
    $test_entity->save();
    $uuid = $test_entity->uuid();

    // Stage the test entity and then delete it from the active storage.
    $active = $this->container->get('config.storage');
    $sync = $this->container->get('config.storage.sync');
    $this->copyConfig($active, $sync);
    $test_entity->delete();

    // Create a content type with a matching UUID in the active storage.
    $content_type = NodeType::create([
      'type' => $this->randomMachineName(16),
      'name' => $this->randomMachineName(),
      'uuid' => $uuid,
    ]);
    $content_type->save();

    // Confirm that the staged configuration is detected as a rename since the
    // UUIDs match.
    $this->configImporter->reset();
    $expected = [
      'node.type.' . $content_type->id() . '::config_test.dynamic.' . $test_entity_id,
    ];
    $renames = $this->configImporter->getUnprocessedConfiguration('rename');
    $this->assertSame($expected, $renames);

    // Try to import the configuration. We expect an exception to be thrown
    // because the staged entity is of a different type.
    try {
      $this->configImporter->import();
      $this->fail('Expected ConfigImporterException thrown when a renamed configuration entity does not match the existing entity type.');
    }
    catch (ConfigImporterException) {
      $expected = [
        "Entity type mismatch on rename. node_type not equal to config_test for existing configuration node.type.{$content_type->id()} and staged configuration config_test.dynamic.$test_entity_id.",
      ];
      $this->assertEquals($expected, $this->configImporter->getErrors());
    }
  }

  /**
   * Tests configuration renaming validation for simple configuration.
   */
  public function testRenameSimpleConfigValidation(): void {
    $uuid = new Php();
    // Create a simple configuration with a UUID.
    $config = $this->config('config_test.new');
    $uuid_value = $uuid->generate();
    $config->set('uuid', $uuid_value)->save();

    $active = $this->container->get('config.storage');
    $sync = $this->container->get('config.storage.sync');
    $this->copyConfig($active, $sync);
    $config->delete();

    // Create another simple configuration with the same UUID.
    $config = $this->config('config_test.old');
    $config->set('uuid', $uuid_value)->save();

    // Confirm that the staged configuration is detected as a rename since the
    // UUIDs match.
    $this->configImporter->reset();
    $expected = [
      'config_test.old::config_test.new',
    ];
    $renames = $this->configImporter->getUnprocessedConfiguration('rename');
    $this->assertSame($expected, $renames);

    // Try to import the configuration. We expect an exception to be thrown
    // because the rename is for simple configuration.
    try {
      $this->configImporter->import();
      $this->fail('Expected ConfigImporterException thrown when simple configuration is renamed.');
    }
    catch (ConfigImporterException) {
      $expected = [
        'Rename operation for simple configuration. Existing configuration config_test.old and staged configuration config_test.new.',
      ];
      $this->assertEquals($expected, $this->configImporter->getErrors());
    }
  }

}
