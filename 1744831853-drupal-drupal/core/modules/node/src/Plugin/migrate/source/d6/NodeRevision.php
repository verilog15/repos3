<?php

namespace Drupal\node\Plugin\migrate\source\d6;

use Drupal\Core\Database\Query\SelectInterface;
use Drupal\migrate\Attribute\MigrateSource;

/**
 * Drupal 6 node revision source from database.
 *
 * For available configuration keys, refer to the parent classes.
 *
 * @see \Drupal\migrate\Plugin\migrate\source\SqlBase
 * @see \Drupal\migrate\Plugin\migrate\source\SourcePluginBase
 */
#[MigrateSource(
  id: 'd6_node_revision',
  source_module: 'node',
)]
class NodeRevision extends Node {

  /**
   * The join options between the node and the node_revisions_table.
   */
  const JOIN = 'n.nid = nr.nid AND n.vid <> nr.vid';

  /**
   * {@inheritdoc}
   */
  public function fields() {
    // Use all the node fields plus the vid that identifies the version.
    return parent::fields() + [
      'vid' => $this->t('The primary identifier for this version.'),
      'log' => $this->t('Revision Log message'),
      'timestamp' => $this->t('Revision timestamp'),
    ];
  }

  /**
   * {@inheritdoc}
   */
  public function getIds() {
    $ids['vid']['type'] = 'integer';
    $ids['vid']['alias'] = 'nr';
    return $ids;
  }

  /**
   * {@inheritdoc}
   */
  protected function handleTranslations(SelectInterface $query) {
    // @todo in https://www.drupal.org/node/2746541
  }

}
