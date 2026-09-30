package keystrokesmod.module.impl.combat.autoclicker;

import keystrokesmod.event.PreMotionEvent;
import keystrokesmod.module.setting.impl.SliderSetting;
import keystrokesmod.module.setting.impl.SubMode;
import keystrokesmod.utility.CoolDown;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import org.jetbrains.annotations.NotNull;
import org.lwjgl.input.Mouse;

public class BlatantAutoClicker extends SubMode<IAutoClicker> {
    private final SliderSetting cps;
    private final boolean leftClick;
    private final boolean always;

    private final CoolDown clickStopWatch = new CoolDown(0);
    private int ticksDown;

    public BlatantAutoClicker(String name, @NotNull IAutoClicker parent, boolean left, boolean always) {
        super(name, parent);
        this.leftClick = left;
        this.always = always;

        cps = new SliderSetting("CPS", 15, 1, 25, 1);
        this.registerSetting(cps);
    }

    @SubscribeEvent
    public void onPreMotion(PreMotionEvent event) {
        // Intervalo fixo baseado no CPS - sem oscilação
        long interval = 1000 / (long) cps.getInput();
        clickStopWatch.setCooldown(interval);
        
        if (clickStopWatch.hasFinished()) {
            if (Mouse.isButtonDown(0) || always) {
                ticksDown++;
            } else {
                ticksDown = 0;
            }

            if (leftClick && ticksDown > 1) {
                parent.click();
            }

            this.clickStopWatch.start();
        }
    }
}

