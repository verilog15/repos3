<?php

declare(strict_types=1);

namespace Drupal\Tests\serialization\Unit\Normalizer;

use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\Core\Config\ImmutableConfig;
use Drupal\Core\Datetime\DrupalDateTime;
use Drupal\Core\Field\FieldDefinitionInterface;
use Drupal\Core\Field\FieldItemBase;
use Drupal\Core\Field\FieldStorageDefinitionInterface;
use Drupal\Core\TypedData\Plugin\DataType\DateTimeIso8601;
use Drupal\Core\TypedData\Plugin\DataType\IntegerData;
use Drupal\Core\TypedData\Type\DateTimeInterface;
use Drupal\datetime\Plugin\Field\FieldType\DateTimeItem;
use Drupal\serialization\Normalizer\DateTimeIso8601Normalizer;
use Drupal\Tests\serialization\Traits\JsonSchemaTestTrait;
use Drupal\Tests\UnitTestCase;
use Prophecy\Argument;
use Symfony\Component\Serializer\Exception\InvalidArgumentException;
use Symfony\Component\Serializer\Exception\UnexpectedValueException;

/**
 * Unit test coverage for the "datetime_iso8601" @DataType.
 *
 * @coversDefaultClass \Drupal\serialization\Normalizer\DateTimeIso8601Normalizer
 * @group serialization
 * @see \Drupal\Core\TypedData\Plugin\DataType\DateTimeIso8601
 * @see \Drupal\datetime\Plugin\Field\FieldType\DateTimeItem::DATETIME_TYPE_DATE
 */
class DateTimeIso8601NormalizerTest extends UnitTestCase {

  use JsonSchemaTestTrait;

  /**
   * The tested data type's normalizer.
   *
   * @var \Drupal\serialization\Normalizer\DateTimeIso8601Normalizer
   */
  protected $normalizer;

  /**
   * The tested data type.
   *
   * @var \Drupal\Core\TypedData\Plugin\DataType\DateTimeIso8601
   */
  protected $data;

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();

    $system_date_config = $this->prophesize(ImmutableConfig::class);
    $system_date_config->get('timezone.default')
      ->willReturn('Australia/Sydney');
    $config_factory = $this->prophesize(ConfigFactoryInterface::class);
    $config_factory->get('system.date')
      ->willReturn($system_date_config->reveal());

    $this->normalizer = new DateTimeIso8601Normalizer($config_factory->reveal());
    $this->data = $this->prophesize(DateTimeIso8601::class);
  }

  /**
   * @covers ::supportsNormalization
   */
  public function testSupportsNormalization(): void {
    $this->assertTrue($this->normalizer->supportsNormalization($this->data->reveal()));

    $datetime = $this->prophesize(DateTimeInterface::class);
    $this->assertFalse($this->normalizer->supportsNormalization($datetime->reveal()));

    $integer = $this->prophesize(IntegerData::class);
    $this->assertFalse($this->normalizer->supportsNormalization($integer->reveal()));
  }

  /**
   * @covers ::supportsDenormalization
   */
  public function testSupportsDenormalization(): void {
    $this->assertTrue($this->normalizer->supportsDenormalization($this->data->reveal(), DateTimeIso8601::class));
  }

  /**
   * @covers ::normalize
   * @dataProvider providerTestNormalize
   */
  public function testNormalize($parent_field_item_class, $datetime_type, $expected_format): void {
    $formatted_string = $this->randomMachineName();

    $field_item = $this->prophesize($parent_field_item_class);
    if ($parent_field_item_class === DateTimeItem::class) {
      $field_storage_definition = $this->prophesize(FieldStorageDefinitionInterface::class);
      $field_storage_definition->getSetting('datetime_type')
        ->willReturn($datetime_type);
      $field_definition = $this->prophesize(FieldDefinitionInterface::class);
      $field_definition->getFieldStorageDefinition()
        ->willReturn($field_storage_definition);
      $field_item->getFieldDefinition()
        ->willReturn($field_definition);
    }
    else {
      $field_item->getFieldDefinition(Argument::any())
        ->shouldNotBeCalled();
    }
    $this->data->getParent()
      ->willReturn($field_item);

    $drupal_date_time = $this->prophesize(DateTimeIso8601NormalizerTestDrupalDateTime::class);
    $drupal_date_time->setTimezone(new \DateTimeZone('Australia/Sydney'))
      ->willReturn($drupal_date_time->reveal());
    $drupal_date_time->format($expected_format)
      ->willReturn($formatted_string);
    $this->data->getDateTime()
      ->willReturn($drupal_date_time->reveal());

    $normalized = $this->normalizer->normalize($this->data->reveal());
    $this->assertSame($formatted_string, $normalized);
  }

  /**
   * @covers ::normalize
   * @dataProvider providerTestNormalize
   */
  public function testNormalizeWhenNull($parent_field_item_class, $datetime_type, $expected_format): void {
    $field_item = $this->prophesize($parent_field_item_class);
    if ($parent_field_item_class === DateTimeItem::class) {
      $field_storage_definition = $this->prophesize(FieldStorageDefinitionInterface::class);
      $field_storage_definition->getSetting('datetime_type')
        ->willReturn($datetime_type);
      $field_definition = $this->prophesize(FieldDefinitionInterface::class);
      $field_definition->getFieldStorageDefinition()
        ->willReturn($field_storage_definition);
      $field_item->getFieldDefinition()
        ->willReturn($field_definition);
    }
    else {
      $field_item->getFieldDefinition(Argument::any())
        ->shouldNotBeCalled();
    }
    $this->data->getParent()
      ->willReturn($field_item);

    $this->data->getDateTime()
      ->willReturn(NULL);

    $normalized = $this->normalizer->normalize($this->data->reveal());
    $this->assertNull($normalized);
  }

  /**
   * Data provider for testNormalize.
   *
   * @return array
   *   The data provider array.
   */
  public static function providerTestNormalize() {
    return [
      // @see \Drupal\datetime\Plugin\Field\FieldType\DateTimeItem::DATETIME_TYPE_DATE
      'datetime field, configured to store only date: must be handled by DateTimeIso8601Normalizer' => [
        DateTimeItem::class,
        DateTimeItem::DATETIME_TYPE_DATE,
        // This expected format call proves that normalization is handled by \Drupal\serialization\Normalizer\DateTimeIso8601Normalizer::normalize().
        'Y-m-d',
      ],
      // @see \Drupal\datetime\Plugin\Field\FieldType\DateTimeItem::DATETIME_TYPE_DATETIME
      'datetime field, configured to store date and time; must be handled by the parent normalizer' => [
        DateTimeItem::class,
        DateTimeItem::DATETIME_TYPE_DATETIME,
        \DateTime::RFC3339,
      ],
      'non-datetime field; must be handled by the parent normalizer' => [
        FieldItemBase::class,
        NULL,
        \DateTime::RFC3339,
      ],

    ];
  }

  /**
   * Tests the denormalize function with good data.
   *
   * @covers ::denormalize
   * @dataProvider providerTestDenormalizeValidFormats
   */
  public function testDenormalizeValidFormats($type, $normalized, $expected): void {
    $field_definition = $this->prophesize(FieldDefinitionInterface::class);
    $field_definition->getSetting('datetime_type')->willReturn($type === 'date-only' ? DateTimeItem::DATETIME_TYPE_DATE : DateTimeItem::DATETIME_TYPE_DATETIME);
    $denormalized = $this->normalizer->denormalize($normalized, DateTimeIso8601::class, NULL, [
      'field_definition' => $field_definition->reveal(),
    ]);
    $this->assertSame($expected, $denormalized);
  }

  /**
   * Data provider for testDenormalizeValidFormats.
   *
   * @return array
   *   An array of test cases.
   */
  public static function providerTestDenormalizeValidFormats() {
    $data = [];
    $data['just a date'] = ['date-only', '2016-11-06', '2016-11-06'];

    $data['RFC3339'] = ['date+time', '2016-11-06T09:02:00+00:00', '2016-11-06T09:02:00'];
    $data['RFC3339 +0100'] = ['date+time', '2016-11-06T09:02:00+01:00', '2016-11-06T08:02:00'];
    $data['RFC3339 -0600'] = ['date+time', '2016-11-06T09:02:00-06:00', '2016-11-06T15:02:00'];

    $data['ISO8601'] = ['date+time', '2016-11-06T09:02:00+0000', '2016-11-06T09:02:00'];
    $data['ISO8601 +0100'] = ['date+time', '2016-11-06T09:02:00+0100', '2016-11-06T08:02:00'];
    $data['ISO8601 -0600'] = ['date+time', '2016-11-06T09:02:00-0600', '2016-11-06T15:02:00'];

    return $data;
  }

  /**
   * Tests the denormalize function with bad data for the date-only case.
   *
   * @covers ::denormalize
   */
  public function testDenormalizeDateOnlyException(): void {
    $this->expectException(UnexpectedValueException::class);
    $this->expectExceptionMessage('The specified date "2016/11/06" is not in an accepted format: "Y-m-d" (date-only).');

    $normalized = '2016/11/06';

    $field_definition = $this->prophesize(FieldDefinitionInterface::class);
    $field_definition->getSetting('datetime_type')->willReturn(DateTimeItem::DATETIME_TYPE_DATE);
    $this->normalizer->denormalize($normalized, DateTimeIso8601::class, NULL, ['field_definition' => $field_definition->reveal()]);
  }

  /**
   * Tests the denormalize function with bad data for the date+time case.
   *
   * @covers ::denormalize
   */
  public function testDenormalizeDateAndTimeException(): void {
    $this->expectException(UnexpectedValueException::class);
    $this->expectExceptionMessage('The specified date "on a rainy day" is not in an accepted format: "Y-m-d\TH:i:sP" (RFC 3339), "Y-m-d\TH:i:sO" (ISO 8601).');

    $normalized = 'on a rainy day';

    $field_definition = $this->prophesize(FieldDefinitionInterface::class);
    $field_definition->getSetting('datetime_type')->willReturn(DateTimeItem::DATETIME_TYPE_DATETIME);
    $this->normalizer->denormalize($normalized, DateTimeIso8601::class, NULL, ['field_definition' => $field_definition->reveal()]);
  }

  /**
   * Tests the denormalize function with incomplete serialization context.
   *
   * @covers ::denormalize
   */
  public function testDenormalizeNoTargetInstanceOrFieldDefinitionException(): void {
    $this->expectException(InvalidArgumentException::class);
    $this->expectExceptionMessage('$context[\'target_instance\'] or $context[\'field_definition\'] must be set to denormalize with the DateTimeIso8601Normalizer');
    $this->normalizer->denormalize('', DateTimeIso8601::class, NULL, []);
  }

  /**
   * {@inheritdoc}
   */
  public static function jsonSchemaDataProvider(): array {
    $case = function (UnitTestCase $test) {
      assert(in_array(JsonSchemaTestTrait::class, class_uses($test)));
      $field_item = $test->doProphesize(DateTimeItem::class);
      $data = $test->doProphesize(DateTimeIso8601::class);

      $field_storage_definition = $test->doProphesize(FieldStorageDefinitionInterface::class);
      $field_storage_definition->getSetting('datetime_type')
        ->willReturn(DateTimeItem::DATETIME_TYPE_DATE);
      $field_definition = $test->doProphesize(FieldDefinitionInterface::class);
      $field_definition->getFieldStorageDefinition()
        ->willReturn($field_storage_definition);
      $field_item->getFieldDefinition()
        ->willReturn($field_definition);
      $data->getParent()
        ->willReturn($field_item);
      $drupal_date_time = $test->doProphesize(DateTimeIso8601NormalizerTestDrupalDateTime::class);
      $drupal_date_time->setTimezone(new \DateTimeZone('Australia/Sydney'))
        ->willReturn($drupal_date_time->reveal());
      $drupal_date_time->format('Y-m-d')
        ->willReturn('1991-09-19');
      $data->getDateTime()
        ->willReturn($drupal_date_time->reveal());
      return $data->reveal();
    };
    return [
      'ISO 8601 date-only' => [fn (UnitTestCase $test) => $case($test)],
    ];
  }

}

/**
 * Provides a test class for testing DrupalDateTime.
 *
 * Note: Prophecy does not support magic methods. By subclassing and specifying
 * an explicit method, Prophecy works.
 *
 * @see https://github.com/phpspec/prophecy/issues/338
 * @see https://github.com/phpspec/prophecy/issues/34
 * @see https://github.com/phpspec/prophecy/issues/80
 */
class DateTimeIso8601NormalizerTestDrupalDateTime extends DrupalDateTime {

  /**
   * Sets the timezone.
   */
  public function setTimezone(\DateTimeZone $timezone) {
    parent::setTimezone($timezone);
  }

}
