package keystrokesmod.module.impl.hg;

import keystrokesmod.event.PreMotionEvent;
import keystrokesmod.module.Module;
import keystrokesmod.module.setting.impl.SliderSetting;
import keystrokesmod.utility.Utils;
import net.minecraft.util.MovingObjectPosition;
import net.minecraft.util.Vec3;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;

public class BlockReach extends Module {
    private final SliderSetting range;

    public BlockReach() {
        super("BlockReach", category.hg, "Aumenta o alcance de colocar blocos");

        this.registerSetting(range = new SliderSetting("Range", 5.0, 3.0, 10.0, 0.5, "blocks"));
    }

    public double getRange() {
        return range.getInput();
    }

    public static double getBlockReach() {
        if (keystrokesmod.module.ModuleManager.blockReach != null && 
            keystrokesmod.module.ModuleManager.blockReach.isEnabled()) {
            return ((BlockReach) keystrokesmod.module.ModuleManager.blockReach).getRange();
        }
        return 4.5; // Alcance padrão do Minecraft
    }

    @Override
    public String getPrettyInfo() {
        return String.format("%.1f", range.getInput());
    }
}

