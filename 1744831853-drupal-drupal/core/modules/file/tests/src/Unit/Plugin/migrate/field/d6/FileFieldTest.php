<?php

declare(strict_types=1);

namespace Drupal\Tests\file\Unit\Plugin\migrate\field\d6;

use Drupal\migrate\Plugin\MigrationInterface;
use Drupal\migrate\Row;
use Drupal\Tests\UnitTestCase;
use Drupal\file\Plugin\migrate\field\d6\FileField;
use Prophecy\Argument;

// cspell:ignore filefield imagefield

/**
 * @coversDefaultClass \Drupal\file\Plugin\migrate\field\d6\FileField
 * @group file
 */
class FileFieldTest extends UnitTestCase {

  /**
   * The migrate field plugin.
   *
   * @var \Drupal\migrate_drupal\Plugin\MigrateFieldInterface
   */
  protected $plugin;

  /**
   * The migration.
   *
   * @var \Drupal\migrate\Plugin\MigrationInterface
   */
  protected $migration;

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();

    $this->plugin = new FileField([], 'file', []);

    $migration = $this->prophesize(MigrationInterface::class);

    // The plugin's defineValueProcessPipeline() method will call
    // mergeProcessOfProperty() and return nothing. So, in order to examine the
    // process pipeline created by the plugin, we need to ensure that
    // getProcess() always returns the last input to mergeProcessOfProperty().
    $migration->mergeProcessOfProperty(Argument::type('string'), Argument::type('array'))
      ->will(function ($arguments) use ($migration) {
        $migration->getProcess()->willReturn($arguments[1]);
      });
    $this->migration = $migration->reveal();
  }

  /**
   * @covers ::defineValueProcessPipeline
   */
  public function testDefineValueProcessPipeline($method = 'defineValueProcessPipeline'): void {
    $this->plugin->$method($this->migration, 'field_name', []);

    $expected = [
      'plugin' => 'd6_field_file',
      'source' => 'field_name',
    ];
    $this->assertSame($expected, $this->migration->getProcess());
  }

  /**
   * Data provider for testGetFieldType().
   */
  public static function getFieldTypeProvider() {
    return [
      ['image', 'imagefield_widget'],
      ['file', 'filefield_widget'],
      ['file', 'x_widget'],
    ];
  }

  /**
   * @covers ::getFieldType
   * @dataProvider getFieldTypeProvider
   */
  public function testGetFieldType($expected_type, $widget_type, array $settings = []): void {
    $row = new Row();
    $row->setSourceProperty('widget_type', $widget_type);
    $row->setSourceProperty('global_settings', $settings);
    $this->assertSame($expected_type, $this->plugin->getFieldType($row));
  }

}
