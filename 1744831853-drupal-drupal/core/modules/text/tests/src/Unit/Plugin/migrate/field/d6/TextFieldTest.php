<?php

declare(strict_types=1);

namespace Drupal\Tests\text\Unit\Plugin\migrate\field\d6;

use Drupal\migrate\Plugin\MigrationInterface;
use Drupal\migrate\Row;
use Drupal\Tests\UnitTestCase;
use Drupal\text\Plugin\migrate\field\d6\TextField;
use Prophecy\Argument;

// cspell:ignore optionwidgets

/**
 * @coversDefaultClass \Drupal\text\Plugin\migrate\field\d6\TextField
 * @group text
 */
class TextFieldTest extends UnitTestCase {

  /**
   * The migration field plugin to test.
   *
   * @var \Drupal\migrate_drupal\Plugin\MigrateFieldInterface
   */
  protected $plugin;

  /**
   * The migration object.
   *
   * @var \Drupal\migrate\Plugin\MigrationInterface
   */
  protected $migration;

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();

    $this->plugin = new TextField([], 'text', []);

    $migration = $this->prophesize(MigrationInterface::class);

    // The plugin's defineValueProcessPipeline() method will call
    // setProcessOfProperty() and return nothing. So, in order to examine the
    // process pipeline created by the plugin, we need to ensure that
    // getProcess() always returns the last input to setProcessOfProperty().
    $migration->setProcessOfProperty(Argument::type('string'), Argument::type('array'))
      ->will(function ($arguments) use ($migration) {
        $migration->getProcess()->willReturn($arguments[1]);
      });

    $this->migration = $migration->reveal();
  }

  /**
   * @covers ::defineValueProcessPipeline
   */
  public function testFilteredTextValueProcessPipeline(): void {
    $field_info = [
      'widget_type' => 'text_textfield',
    ];
    $this->plugin->defineValueProcessPipeline($this->migration, 'body', $field_info);

    $process = $this->migration->getProcess();
    $this->assertSame('sub_process', $process['plugin']);
    $this->assertSame('body', $process['source']);
    $this->assertSame('value', $process['process']['value']);

    // Ensure that filter format IDs will be looked up in the filter format
    // migrations.
    $lookup = $process['process']['format'][2];
    $this->assertSame('migration_lookup', $lookup['plugin']);
    $this->assertContains('d6_filter_format', $lookup['migration']);
    $this->assertContains('d7_filter_format', $lookup['migration']);
    $this->assertSame('format', $lookup['source']);
  }

  /**
   * @covers ::defineValueProcessPipeline
   */
  public function testBooleanTextImplicitValueProcessPipeline(): void {
    $info = [
      'widget_type' => 'optionwidgets_onoff',
      'global_settings' => [
        'allowed_values' => "foo\nbar",
      ],
    ];
    $this->plugin->defineValueProcessPipeline($this->migration, 'field', $info);

    $expected = [
      'value' => [
        'plugin' => 'static_map',
        'source' => 'value',
        'default_value' => 0,
        'map' => [
          'bar' => 1,
        ],
      ],
    ];
    $this->assertSame($expected, $this->migration->getProcess()['process']);
  }

  /**
   * @covers ::defineValueProcessPipeline
   */
  public function testBooleanTextExplicitValueProcessPipeline(): void {
    $info = [
      'widget_type' => 'optionwidgets_onoff',
      'global_settings' => [
        'allowed_values' => "foo|Foo\nBaz|Baz",
      ],
    ];
    $this->plugin->defineValueProcessPipeline($this->migration, 'field', $info);

    $expected = [
      'value' => [
        'plugin' => 'static_map',
        'source' => 'value',
        'default_value' => 0,
        'map' => [
          'Baz' => 1,
        ],
      ],
    ];
    $this->assertSame($expected, $this->migration->getProcess()['process']);
  }

  /**
   * Data provider for testGetFieldType().
   */
  public static function getFieldTypeProvider() {
    return [
      ['string_long', 'text_textfield', ['text_processing' => FALSE]],
      ['string', 'text_textfield', [
        'text_processing' => FALSE,
        'max_length' => 128,
      ],
      ],
      ['string_long', 'text_textfield', [
        'text_processing' => FALSE,
        'max_length' => 4096,
      ],
      ],
      ['text_long', 'text_textfield', ['text_processing' => TRUE]],
      ['text', 'text_textfield', [
        'text_processing' => TRUE,
        'max_length' => 128,
      ],
      ],
      ['text_long', 'text_textfield', [
        'text_processing' => TRUE,
        'max_length' => 4096,
      ],
      ],
      ['list_string', 'optionwidgets_buttons'],
      ['list_string', 'optionwidgets_select'],
      ['boolean', 'optionwidgets_onoff'],
      ['text_long', 'text_textarea', ['text_processing' => TRUE]],
      ['string_long', 'text_textarea', ['text_processing' => FALSE]],
      [NULL, 'undefined'],
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
