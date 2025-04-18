<?php

declare(strict_types=1);

namespace Drupal\Tests\search\Unit;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\search\Entity\SearchPage;
use Drupal\search\SearchPageRepository;
use Drupal\Tests\UnitTestCase;

/**
 * @coversDefaultClass \Drupal\search\SearchPageRepository
 * @group search
 */
class SearchPageRepositoryTest extends UnitTestCase {

  /**
   * The search page repository.
   *
   * @var \Drupal\search\SearchPageRepository
   */
  protected $searchPageRepository;

  /**
   * The entity query object.
   *
   * @var \Drupal\Core\Entity\Query\QueryInterface|\PHPUnit\Framework\MockObject\MockObject
   */
  protected $query;

  /**
   * The search page storage.
   *
   * @var \Drupal\Core\Config\Entity\ConfigEntityStorageInterface|\PHPUnit\Framework\MockObject\MockObject
   */
  protected $storage;

  /**
   * The config factory.
   *
   * @var \Drupal\Core\Config\ConfigFactoryInterface|\PHPUnit\Framework\MockObject\MockObject
   */
  protected $configFactory;

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();

    $this->query = $this->createMock('Drupal\Core\Entity\Query\QueryInterface');

    $this->storage = $this->createMock('Drupal\Core\Config\Entity\ConfigEntityStorageInterface');
    $this->storage->expects($this->any())
      ->method('getQuery')
      ->willReturn($this->query);

    /** @var \Drupal\Core\Entity\EntityTypeManagerInterface|\PHPUnit\Framework\MockObject\MockObject $entity_type_manager */
    $entity_type_manager = $this->createMock(EntityTypeManagerInterface::class);
    $entity_type_manager->expects($this->any())
      ->method('getStorage')
      ->willReturn($this->storage);

    $this->configFactory = $this->createMock('Drupal\Core\Config\ConfigFactoryInterface');
    $this->searchPageRepository = new SearchPageRepository($this->configFactory, $entity_type_manager);
  }

  /**
   * Tests the getActiveSearchPages() method.
   */
  public function testGetActiveSearchPages(): void {
    $this->query->expects($this->once())
      ->method('condition')
      ->with('status', TRUE)
      ->willReturn($this->query);
    $this->query->expects($this->once())
      ->method('execute')
      ->willReturn(['test' => 'test', 'other_test' => 'other_test']);

    $entities = [];
    $entities['test'] = $this->createMock('Drupal\search\SearchPageInterface');
    $entities['other_test'] = $this->createMock('Drupal\search\SearchPageInterface');
    $this->storage->expects($this->once())
      ->method('loadMultiple')
      ->with(['test' => 'test', 'other_test' => 'other_test'])
      ->willReturn($entities);

    $result = $this->searchPageRepository->getActiveSearchPages();
    $this->assertSame($entities, $result);
  }

  /**
   * Tests the isSearchActive() method.
   */
  public function testIsSearchActive(): void {
    $this->query->expects($this->once())
      ->method('condition')
      ->with('status', TRUE)
      ->willReturn($this->query);
    $this->query->expects($this->once())
      ->method('range')
      ->with(0, 1)
      ->willReturn($this->query);
    $this->query->expects($this->once())
      ->method('execute')
      ->willReturn(['test' => 'test']);

    $this->assertTrue($this->searchPageRepository->isSearchActive());
  }

  /**
   * Tests the getIndexableSearchPages() method.
   */
  public function testGetIndexableSearchPages(): void {
    $this->query->expects($this->once())
      ->method('condition')
      ->with('status', TRUE)
      ->willReturn($this->query);
    $this->query->expects($this->once())
      ->method('execute')
      ->willReturn(['test' => 'test', 'other_test' => 'other_test']);

    $entities = [];
    $entities['test'] = $this->createMock('Drupal\search\SearchPageInterface');
    $entities['test']->expects($this->once())
      ->method('isIndexable')
      ->willReturn(TRUE);
    $entities['other_test'] = $this->createMock('Drupal\search\SearchPageInterface');
    $entities['other_test']->expects($this->once())
      ->method('isIndexable')
      ->willReturn(FALSE);
    $this->storage->expects($this->once())
      ->method('loadMultiple')
      ->with(['test' => 'test', 'other_test' => 'other_test'])
      ->willReturn($entities);

    $result = $this->searchPageRepository->getIndexableSearchPages();
    $this->assertCount(1, $result);
    $this->assertSame($entities['test'], reset($result));
  }

  /**
   * Tests the clearDefaultSearchPage() method.
   */
  public function testClearDefaultSearchPage(): void {
    $config = $this->getMockBuilder('Drupal\Core\Config\Config')
      ->disableOriginalConstructor()
      ->getMock();
    $config->expects($this->once())
      ->method('clear')
      ->with('default_page')
      ->willReturn($config);
    $this->configFactory->expects($this->once())
      ->method('getEditable')
      ->with('search.settings')
      ->willReturn($config);
    $this->searchPageRepository->clearDefaultSearchPage();
  }

  /**
   * Tests the getDefaultSearchPage() method when the default is active.
   */
  public function testGetDefaultSearchPageWithActiveDefault(): void {
    $this->query->expects($this->once())
      ->method('condition')
      ->with('status', TRUE)
      ->willReturn($this->query);
    $this->query->expects($this->once())
      ->method('execute')
      ->willReturn(['test' => 'test', 'other_test' => 'other_test']);

    $config = $this->getMockBuilder('Drupal\Core\Config\Config')
      ->disableOriginalConstructor()
      ->getMock();
    $config->expects($this->once())
      ->method('get')
      ->with('default_page')
      ->willReturn('test');
    $this->configFactory->expects($this->once())
      ->method('get')
      ->with('search.settings')
      ->willReturn($config);

    $this->assertSame('test', $this->searchPageRepository->getDefaultSearchPage());
  }

  /**
   * Tests the getDefaultSearchPage() method when the default is inactive.
   */
  public function testGetDefaultSearchPageWithInactiveDefault(): void {
    $this->query->expects($this->once())
      ->method('condition')
      ->with('status', TRUE)
      ->willReturn($this->query);
    $this->query->expects($this->once())
      ->method('execute')
      ->willReturn(['test' => 'test']);

    $config = $this->getMockBuilder('Drupal\Core\Config\Config')
      ->disableOriginalConstructor()
      ->getMock();
    $config->expects($this->once())
      ->method('get')
      ->with('default_page')
      ->willReturn('other_test');
    $this->configFactory->expects($this->once())
      ->method('get')
      ->with('search.settings')
      ->willReturn($config);

    $this->assertSame('test', $this->searchPageRepository->getDefaultSearchPage());
  }

  /**
   * Tests the setDefaultSearchPage() method.
   */
  public function testSetDefaultSearchPage(): void {
    $id = 'bananas';
    $config = $this->getMockBuilder('Drupal\Core\Config\Config')
      ->disableOriginalConstructor()
      ->getMock();
    $config->expects($this->once())
      ->method('set')
      ->with('default_page', $id)
      ->willReturn($config);
    $config->expects($this->once())
      ->method('save')
      ->willReturn($config);
    $this->configFactory->expects($this->once())
      ->method('getEditable')
      ->with('search.settings')
      ->willReturn($config);

    $search_page = $this->createMock('Drupal\search\SearchPageInterface');
    $search_page->expects($this->once())
      ->method('id')
      ->willReturn($id);
    $search_page->expects($this->once())
      ->method('enable')
      ->willReturn($search_page);
    $search_page->expects($this->once())
      ->method('save')
      ->willReturn($search_page);
    $this->searchPageRepository->setDefaultSearchPage($search_page);
  }

  /**
   * Tests the sortSearchPages() method.
   */
  public function testSortSearchPages(): void {
    $entity_type = $this->createMock(EntityTypeInterface::class);
    $entity_type
      ->method('getClass')
      ->willReturn(TestSearchPage::class);
    $this->storage->expects($this->once())
      ->method('getEntityType')
      ->willReturn($entity_type);

    // Declare entities out of their expected order, so we can be sure they were
    // sorted.
    $entity_test4 = $this->createMock(TestSearchPage::class);
    $entity_test4
      ->method('label')
      ->willReturn('Test4');
    $entity_test4
      ->method('status')
      ->willReturn(FALSE);
    $entity_test4
      ->method('getWeight')
      ->willReturn(0);
    $entity_test3 = $this->createMock(TestSearchPage::class);
    $entity_test3
      ->method('label')
      ->willReturn('Test3');
    $entity_test3
      ->method('status')
      ->willReturn(FALSE);
    $entity_test3
      ->method('getWeight')
      ->willReturn(10);
    $entity_test2 = $this->createMock(TestSearchPage::class);
    $entity_test2
      ->method('label')
      ->willReturn('Test2');
    $entity_test2
      ->method('status')
      ->willReturn(TRUE);
    $entity_test2
      ->method('getWeight')
      ->willReturn(0);
    $entity_test1 = $this->createMock(TestSearchPage::class);
    $entity_test1
      ->method('label')
      ->willReturn('Test1');
    $entity_test1
      ->method('status')
      ->willReturn(TRUE);
    $entity_test1
      ->method('getWeight')
      ->willReturn(0);

    $unsorted_entities = [$entity_test4, $entity_test3, $entity_test2, $entity_test1];
    $expected = [$entity_test1, $entity_test2, $entity_test3, $entity_test4];

    $sorted_entities = $this->searchPageRepository->sortSearchPages($unsorted_entities);
    $this->assertSame($expected, array_values($sorted_entities));
  }

}

/**
 * Mock for the configured search page entity.
 */
class TestSearchPage extends SearchPage {

  public function __construct(array $values) {
    foreach ($values as $key => $value) {
      $this->$key = $value;
    }
  }

  /**
   * {@inheritdoc}
   */
  public function label($langcode = NULL) {
    return $this->label;
  }

}
