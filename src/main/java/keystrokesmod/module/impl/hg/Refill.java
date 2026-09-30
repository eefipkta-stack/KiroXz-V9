package keystrokesmod.module.impl.hg;

import keystrokesmod.event.PreUpdateEvent;
import keystrokesmod.module.Module;
import keystrokesmod.module.setting.impl.ButtonSetting;
import keystrokesmod.module.setting.impl.ModeSetting;
import keystrokesmod.module.setting.impl.SliderSetting;
import keystrokesmod.utility.Utils;
import net.minecraft.client.gui.inventory.GuiInventory;
import net.minecraft.init.Items;
import net.minecraft.inventory.Container;
import net.minecraft.inventory.Slot;
import net.minecraft.item.Item;
import net.minecraft.item.ItemPotion;
import net.minecraft.item.ItemStack;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import org.lwjgl.input.Keyboard;

public class Refill extends Module {
    private final ModeSetting mode;
    private final SliderSetting speed;
    private final ButtonSetting smartSpeed;

    private boolean refilling = false;
    private boolean keyWasPressed = false;
    private int refillTicks = 0;
    private int currentHotbarSlot = 0;

    // Hotbar: slots 36-44 (container IDs)
    private static final int HOTBAR_START = 36;
    private static final int HOTBAR_END = 44;
    
    // Inventário principal: slots 9-35 (container IDs)
    private static final int INVENTORY_START = 9;
    private static final int INVENTORY_END = 35;

    public Refill() {
        super("Refill", category.hg, "Move itens automaticamente para a hotbar");

        this.registerSetting(mode = new ModeSetting("Mode", new String[]{
                "Soup",
                "Potion"
        }, 0));
        this.registerSetting(speed = new SliderSetting("Speed", 5, 1, 10, 1, "x"));
        this.registerSetting(smartSpeed = new ButtonSetting("Smart speed", true));
    }

    @Override
    public void onEnable() {
        refilling = false;
        refillTicks = 0;
        currentHotbarSlot = 0;
    }

    @Override
    public void onDisable() {
        if (refilling && mc.currentScreen instanceof GuiInventory) {
            mc.thePlayer.closeScreen();
        }
        refilling = false;
    }

    @Override
    public void keybind() {
    }

    @SubscribeEvent
    public void onPreUpdate(PreUpdateEvent event) {
        if (!Utils.nullCheck()) return;

        // Não funciona com chat aberto
        if (mc.currentScreen instanceof net.minecraft.client.gui.GuiChat) {
            keyWasPressed = false;
            return;
        }

        // Detecta a tecla
        if (this.getKeycode() != 0) {
            boolean keyIsPressed = Keyboard.isKeyDown(this.getKeycode());
            
            if (keyIsPressed && !keyWasPressed && !refilling) {
                startRefill();
            }
            
            keyWasPressed = keyIsPressed;
        }

        // Processa o refill
        if (refilling) {
            processRefill();
        }
    }

    private void startRefill() {
        // Abre o inventário se não estiver aberto
        if (!(mc.currentScreen instanceof GuiInventory)) {
            mc.displayGuiScreen(new GuiInventory(mc.thePlayer));
        }

        refilling = true;
        refillTicks = 0;
        currentHotbarSlot = 0;
    }

    private void processRefill() {
        // Verifica se o inventário está aberto
        if (!(mc.currentScreen instanceof GuiInventory)) {
            refilling = false;
            return;
        }

        // Calcula o delay baseado na velocidade (10% mais lento para ser mais seguro)
        int speedValue = (int) speed.getInput();
        int delayTicks;
        
        // Multiplicador base (10% mais lento)
        // Speed 4 é SIGNIFICATIVAMENTE mais rápido (50% mais rápido)
        double multiplier = (speedValue == 4) ? 0.5 : 1.1;
        
        if (smartSpeed.isToggled()) {
            // Smart speed: mais rápido quando tem mais itens para mover
            delayTicks = (int) Math.max(0, (6 - speedValue) * multiplier);
        } else {
            // Speed normal: delay fixo
            delayTicks = (int) Math.max(0, (11 - speedValue) * multiplier);
        }

        refillTicks++;
        if (refillTicks < delayTicks) {
            return;
        }
        refillTicks = 0;

        // Move um item para a hotbar
        boolean movedItem = moveNextItemToHotbar();

        if (!movedItem) {
            // Não tem mais itens para mover, finaliza
            mc.thePlayer.closeScreen();
            refilling = false;
        }
    }

    private boolean moveNextItemToHotbar() {
        Container container = mc.thePlayer.inventoryContainer;
        int modeIndex = (int) mode.getInput();
        
        // Encontra o próximo slot vazio na hotbar
        int emptyHotbarSlot = findNextEmptyHotbarSlot();
        
        if (emptyHotbarSlot == -1) {
            // Hotbar cheia, finaliza
            return false;
        }

        // Procura o item desejado no inventário principal
        int itemSlot = -1;
        
        if (modeIndex == 0) {
            // Modo Soup: procura sopas
            itemSlot = findItemInInventory(Items.mushroom_stew);
        } else {
            // Modo Potion: procura poções
            itemSlot = findPotionInInventory();
        }

        if (itemSlot == -1) {
            // Não tem mais itens para mover
            return false;
        }

        // Move o item do inventário para a hotbar
        // Shift+Click move automaticamente para a hotbar
        mc.playerController.windowClick(container.windowId, itemSlot, 0, 1, mc.thePlayer);

        return true;
    }

    private int findNextEmptyHotbarSlot() {
        Container container = mc.thePlayer.inventoryContainer;
        
        for (int i = HOTBAR_START; i <= HOTBAR_END; i++) {
            Slot slot = container.getSlot(i);
            if (!slot.getHasStack()) {
                return i;
            }
        }
        
        return -1; // Hotbar cheia
    }

    private int findItemInInventory(Item item) {
        Container container = mc.thePlayer.inventoryContainer;
        
        // Procura no inventário principal (não na hotbar)
        for (int i = INVENTORY_START; i <= INVENTORY_END; i++) {
            Slot slot = container.getSlot(i);
            if (slot.getHasStack() && slot.getStack().getItem() == item) {
                return i;
            }
        }
        
        return -1;
    }

    private int findPotionInInventory() {
        Container container = mc.thePlayer.inventoryContainer;
        
        // Procura poções splash no inventário principal
        for (int i = INVENTORY_START; i <= INVENTORY_END; i++) {
            Slot slot = container.getSlot(i);
            if (slot.getHasStack()) {
                ItemStack stack = slot.getStack();
                if (stack.getItem() instanceof ItemPotion && ItemPotion.isSplash(stack.getMetadata())) {
                    return i;
                }
            }
        }
        
        return -1;
    }

    @Override
    public String getPrettyInfo() {
        String[] modes = {"Soup", "Potion"};
        int index = (int) mode.getInput();
        return index >= 0 && index < modes.length ? modes[index] : "";
    }
}

