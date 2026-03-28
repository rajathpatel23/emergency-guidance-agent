import { ProtobufFrameSerializer } from "@pipecat-ai/websocket-transport";

/**
 * ReconnectingWebSocket normalizes binary frames to Uint8Array (see pipecat
 * websocket-transport `_handleMessage`). ProtobufFrameSerializer.deserialize
 * only accepts Blob, so every audio frame threw and nothing reached the speaker.
 */
export class ProtobufFrameSerializerCompat extends ProtobufFrameSerializer {
  override async deserialize(
    data: Blob | Uint8Array | ArrayBuffer,
  ): ReturnType<ProtobufFrameSerializer["deserialize"]> {
    if (data instanceof Blob) return super.deserialize(data);
    if (data instanceof Uint8Array) {
      const copy = data.slice();
      return super.deserialize(new Blob([copy]));
    }
    if (data instanceof ArrayBuffer) return super.deserialize(new Blob([new Uint8Array(data)]));
    throw new Error("Unknown websocket binary message type");
  }
}
