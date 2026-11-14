import { Composition } from "remotion";
import { VeniceColdOpen } from "./compositions/VeniceColdOpen";
import {
  S1ColdOpen,
  S2LagoonMap,
  S3Foundations,
  S4Stats,
  S5Mose,
  S6Closing,
} from "./compositions/Sample60";
import { DynamicDocumentary } from "./compositions/DynamicDocumentary";

const HD = { fps: 30, width: 1920, height: 1080 } as const;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Original 720p template kept for reference */}
      <Composition
        id="VeniceColdOpen"
        component={VeniceColdOpen}
        durationInFrames={240}
        fps={30}
        width={1280}
        height={720}
      />
      {/* 60-second sample scenes — 1080p */}
      <Composition id="S1ColdOpen" component={S1ColdOpen} durationInFrames={253} {...HD} />
      <Composition id="S2LagoonMap" component={S2LagoonMap} durationInFrames={313} {...HD} />
      <Composition id="S3Foundations" component={S3Foundations} durationInFrames={372} {...HD} />
      <Composition id="S4Stats" component={S4Stats} durationInFrames={372} {...HD} />
      <Composition id="S5Mose" component={S5Mose} durationInFrames={313} {...HD} />
      <Composition id="S6Closing" component={S6Closing} durationInFrames={252} {...HD} />
      {/* Dynamic documentary composition — reads scene manifest from inputProps */}
      <Composition
        id="DynamicDocumentary"
        component={DynamicDocumentary}
        durationInFrames={18000} // 10 minutes at 30fps - will be overridden by inputProps
        {...HD}
      />
    </>
  );
};
