<?php

declare(strict_types=1);

namespace Drupal\rest_test\Plugin\rest\resource;

use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\rest\Attribute\RestResource;
use Drupal\rest\Plugin\ResourceBase;
use Drupal\rest\ResourceResponse;

/**
 * Class used to test that serialization_class is optional.
 */
#[RestResource(
  id: "serialization_test",
  label: new TranslatableMarkup("Optional serialization_class"),
  serialization_class: "",
  uri_paths: []
)]
class NoSerializationClassTestResource extends ResourceBase {

  /**
   * Responds to a POST request.
   *
   * @param array $data
   *   An array with the payload.
   *
   * @return \Drupal\rest\ResourceResponse
   *   The HTTP response object.
   */
  public function post(array $data) {
    return new ResourceResponse($data);
  }

}
