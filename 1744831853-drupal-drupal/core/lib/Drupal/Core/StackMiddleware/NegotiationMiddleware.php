<?php

namespace Drupal\Core\StackMiddleware;

use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\HttpKernel\HttpKernelInterface;

/**
 * Provides a middleware to determine the content type upon the accept header.
 */
class NegotiationMiddleware implements HttpKernelInterface {

  /**
   * The wrapped HTTP kernel.
   *
   * @var \Symfony\Component\HttpKernel\HttpKernelInterface
   */
  protected $httpKernel;

  /**
   * Contains a hashmap of format as key and mimetype as value.
   *
   * @var array
   */
  protected $formats = [];

  /**
   * Constructs a new NegotiationMiddleware.
   *
   * @param \Symfony\Component\HttpKernel\HttpKernelInterface $http_kernel
   *   The wrapper HTTP kernel.
   */
  public function __construct(HttpKernelInterface $http_kernel) {
    $this->httpKernel = $http_kernel;
  }

  /**
   * {@inheritdoc}
   */
  public function handle(Request $request, $type = self::MAIN_REQUEST, $catch = TRUE): Response {
    // Register available mime types.
    foreach ($this->formats as $format => $mime_type) {
      $request->setFormat($format, $mime_type);
    }

    // Determine the request format using the negotiator.
    if ($requested_format = $this->getContentType($request)) {
      $request->setRequestFormat($requested_format);
    }
    return $this->httpKernel->handle($request, $type, $catch);
  }

  /**
   * Registers a format for a given MIME type.
   *
   * @param string $format
   *   The format.
   * @param string $mime_type
   *   The MIME type.
   *
   * @return $this
   */
  public function registerFormat($format, $mime_type) {
    $this->formats[$format] = $mime_type;
    return $this;
  }

  /**
   * Gets the normalized type of a request.
   *
   * The normalized type is a short, lowercase version of the format, such as
   * 'html', 'json' or 'atom'.
   *
   * @param \Symfony\Component\HttpFoundation\Request $request
   *   The request object from which to extract the content type.
   *
   * @return string
   *   The normalized type of a given request.
   */
  protected function getContentType(Request $request) {
    // AJAX iframe uploads need special handling, because they contain a JSON
    // response wrapped in <textarea>.
    if ($request->request->get('ajax_iframe_upload', FALSE)) {
      return 'iframeupload';
    }

    if ($request->query->has('_format')) {
      return $request->query->get('_format');
    }

    // No format was specified in the request.
    return NULL;
  }

}
