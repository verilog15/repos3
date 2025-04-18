<?php

declare(strict_types=1);

namespace Drupal\Tests\mysql\Unit;

use Drupal\mysql\Driver\Database\mysql\Connection;
use Drupal\mysql\Driver\Database\mysql\Install\Tasks;
use Drupal\Tests\UnitTestCase;

/**
 * Tests the MySQL install tasks.
 *
 * @coversDefaultClass \Drupal\mysql\Driver\Database\mysql\Install\Tasks
 * @group Database
 */
class InstallTasksTest extends UnitTestCase {

  /**
   * A connection object prophecy.
   *
   * @var \Drupal\mysql\Driver\Database\mysql\Connection|\Prophecy\Prophecy\ObjectProphecy
   */
  private $connection;

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();

    $this->connection = $this->prophesize(Connection::class);
  }

  /**
   * Creates a Tasks object for testing.
   *
   * @return \Drupal\mysql\Driver\Database\mysql\Install\Tasks
   *   A Tasks object.
   */
  private function createTasks(): Tasks {
    /** @var \Drupal\mysql\Driver\Database\mysql\Connection $connection */
    $connection = $this->connection->reveal();

    return new class($connection) extends Tasks {

      /**
       * The database connection.
       *
       * @var \Drupal\Core\Database\Connection
       */
      private $connection;

      public function __construct(Connection $connection) {
        $this->connection = $connection;
      }

      /**
       * {@inheritdoc}
       */
      protected function isConnectionActive() {
        return TRUE;
      }

      /**
       * {@inheritdoc}
       */
      protected function getConnection() {
        return $this->connection;
      }

      /**
       * {@inheritdoc}
       */
      protected function t($string, array $args = [], array $options = []) {
        return $string;
      }

    };
  }

  /**
   * Creates a Tasks object for testing, without connection.
   *
   * @return \Drupal\mysql\Driver\Database\mysql\Install\Tasks
   *   A Tasks object.
   */
  private function createTasksNoConnection(): Tasks {
    return new class() extends Tasks {

      /**
       * {@inheritdoc}
       */
      protected function isConnectionActive() {
        return FALSE;
      }

      /**
       * {@inheritdoc}
       */
      protected function getConnection() {
        return NULL;
      }

      /**
       * {@inheritdoc}
       */
      protected function t($string, array $args = [], array $options = []) {
        return $string;
      }

    };
  }

  /**
   * @covers ::minimumVersion
   * @covers ::name
   * @dataProvider providerNameAndMinimumVersion
   */
  public function testNameAndMinimumVersion(bool $is_mariadb, string $expected_name, string $expected_minimum_version): void {
    $this->connection
      ->isMariaDb()
      ->shouldBeCalledTimes(2)
      ->willReturn($is_mariadb);
    $tasks = $this->createTasks();

    $minimum_version = $tasks->minimumVersion();
    $name = $tasks->name();

    $this->assertSame($expected_minimum_version, $minimum_version);
    $this->assertSame($expected_name, $name);

  }

  /**
   * Provides test data.
   *
   * @return array
   *   An array of test data.
   */
  public static function providerNameAndMinimumVersion(): array {
    return [
      [
        TRUE,
        'MariaDB',
        Tasks::MARIADB_MINIMUM_VERSION,
      ],
      [
        FALSE,
        'MySQL, Percona Server, or equivalent',
        Tasks::MYSQL_MINIMUM_VERSION,
      ],
    ];
  }

  /**
   * @covers ::name
   */
  public function testNameWithNoConnection(): void {
    $tasks = $this->createTasksNoConnection();
    $this->assertSame('MySQL, MariaDB, Percona Server, or equivalent', $tasks->name());
  }

}
