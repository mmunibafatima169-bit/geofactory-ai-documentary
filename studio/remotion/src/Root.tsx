import { Composition } from "remotion";
import { VeniceColdOpen } from "./compositions/VeniceColdOpen";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="VeniceColdOpen"
        component={VeniceColdOpen}
        durationInFrames={240}
        fps={30}
        width={1280}
        height={720}
      />
    </>
  );
};
