<?php

declare(strict_types=1);

namespace Drupal\Tests\serialization\Unit\Encoder;

use Drupal\serialization\Encoder\XmlEncoder;
use Symfony\Component\Serializer\Encoder\XmlEncoder as BaseXmlEncoder;
use Symfony\Component\Serializer\Normalizer\GetSetMethodNormalizer;
use Symfony\Component\Serializer\Serializer;
use Drupal\Tests\UnitTestCase;

/**
 * @coversDefaultClass \Drupal\serialization\Encoder\XmlEncoder
 * @group serialization
 */
class XmlEncoderTest extends UnitTestCase {

  /**
   * The XmlEncoder instance.
   *
   * @var \Drupal\serialization\Encoder\XmlEncoder
   */
  protected $encoder;

  /**
   * The Symfony XML encoder.
   *
   * @var \Symfony\Component\Serializer\Encoder\XmlEncoder|\PHPUnit\Framework\MockObject\MockObject
   */
  protected $baseEncoder;

  /**
   * An array of test data.
   *
   * @var array
   */
  protected $testArray = ['test' => 'test'];

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();

    $this->baseEncoder = $this->createMock(BaseXmlEncoder::class);
    $this->encoder = new XmlEncoder();
    $this->encoder->setBaseEncoder($this->baseEncoder);
  }

  /**
   * Tests the supportsEncoding() method.
   */
  public function testSupportsEncoding(): void {
    $this->assertTrue($this->encoder->supportsEncoding('xml'));
    $this->assertFalse($this->encoder->supportsEncoding('json'));
  }

  /**
   * Tests the supportsDecoding() method.
   */
  public function testSupportsDecoding(): void {
    $this->assertTrue($this->encoder->supportsDecoding('xml'));
    $this->assertFalse($this->encoder->supportsDecoding('json'));
  }

  /**
   * Tests the encode() method.
   */
  public function testEncode(): void {
    $this->baseEncoder->expects($this->once())
      ->method('encode')
      ->with($this->testArray, 'test', [])
      ->willReturn('test');

    $this->assertEquals('test', $this->encoder->encode($this->testArray, 'test'));
  }

  /**
   * Tests the decode() method.
   */
  public function testDecode(): void {
    $this->baseEncoder->expects($this->once())
      ->method('decode')
      ->with('test', 'test', [])
      ->willReturn($this->testArray);

    $this->assertEquals($this->testArray, $this->encoder->decode('test', 'test'));
  }

  /**
   * @covers ::getBaseEncoder
   */
  public function testDefaultEncoderHasSerializer(): void {
    // The serializer should be set on the Drupal encoder, which should then
    // set it on our default encoder.
    $encoder = new XmlEncoder();
    $serializer = new Serializer([new GetSetMethodNormalizer()]);
    $encoder->setSerializer($serializer);
    $base_encoder = $encoder->getBaseEncoder();
    $this->assertInstanceOf(BaseXmlEncoder::class, $base_encoder);
    // Test the encoder.
    $base_encoder->encode(['a' => new TestObject()], 'xml');
  }

}

/**
 * Test class used for the encoding test.
 */
class TestObject {

  /**
   * Return the characters "A".
   */
  public function getA() {
    return 'A';
  }

}
