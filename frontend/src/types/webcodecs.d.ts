interface MediaStreamTrackProcessorInit {
  track: MediaStreamTrack;
}

interface MediaStreamTrackProcessor<T = AudioData> {
  readonly readable: ReadableStream<T>;
}

declare var MediaStreamTrackProcessor: {
  prototype: MediaStreamTrackProcessor;
  new(init: MediaStreamTrackProcessorInit): MediaStreamTrackProcessor;
};