<?php

declare(strict_types=1);

namespace Drupal\Tests\migrate\Unit\destination;

use Drupal\migrate\Plugin\migrate\destination\ComponentEntityDisplayBase;
use Drupal\migrate\Row;
use Drupal\Tests\migrate\Unit\MigrateTestCase;

/**
 * Tests the entity display destination plugin.
 *
 * @group migrate
 */
class PerComponentEntityDisplayTest extends MigrateTestCase {

  /**
   * Tests the entity display import method.
   */
  public function testImport(): void {
    $values = [
      'entity_type' => 'entity_type_test',
      'bundle' => 'bundle_test',
      'view_mode' => 'view_mode_test',
      'field_name' => 'field_name_test',
      'options' => ['test setting'],
    ];
    $row = new Row();
    foreach ($values as $key => $value) {
      $row->setDestinationProperty($key, $value);
    }
    $entity = $this->getMockBuilder('Drupal\Core\Entity\Entity\EntityViewDisplay')
      ->disableOriginalConstructor()
      ->getMock();
    $entity->expects($this->once())
      ->method('setComponent')
      ->with('field_name_test', ['test setting'])
      ->willReturnSelf();
    $entity->expects($this->once())
      ->method('save')
      ->with();
    $plugin = new TestPerComponentEntityDisplay($entity);
    $this->assertSame(['entity_type_test', 'bundle_test', 'view_mode_test', 'field_name_test'], $plugin->import($row));
    $this->assertSame(['entity_type_test', 'bundle_test', 'view_mode_test'], $plugin->getTestValues());
  }

}

/**
 * Test class used for testing per component entity display.
 */
class TestPerComponentEntityDisplay extends ComponentEntityDisplayBase {
  const MODE_NAME = 'view_mode';

  /**
   * The arguments of getEntity.
   *
   * @var string[]
   */
  protected $testValues;

  /**
   * The test entity.
   *
   * @var \PHPUnit\Framework\MockObject\MockObject
   */
  protected $entity;

  public function __construct($entity) {
    $this->entity = $entity;
  }

  /**
   * Gets the test entity.
   */
  protected function getEntity($entity_type, $bundle, $view_mode) {
    $this->testValues = func_get_args();
    return $this->entity;
  }

  /**
   * Gets the test values.
   */
  public function getTestValues() {
    return $this->testValues;
  }

}
