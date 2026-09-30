package keystrokesmod.module.impl.hg;

import keystrokesmod.event.PreUpdateEvent;
import keystrokesmod.module.Module;
import keystrokesmod.module.ModuleManager;
import keystrokesmod.module.setting.impl.ButtonSetting;
import keystrokesmod.module.setting.impl.ModeSetting;
import keystrokesmod.module.setting.impl.SliderSetting;
import keystrokesmod.utility.Utils;
import net.minecraft.client.gui.GuiChat;
import net.minecraft.client.gui.inventory.GuiInventory;
import net.minecraft.init.Blocks;
import net.minecraft.init.Items;
import net.minecraft.inventory.Container;
import net.minecraft.inventory.Slot;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import org.lwjgl.input.Keyboard;

public class Recraft extends Module {
    private final ModeSetting mode;
    private final SliderSetting craftSpeed;
    private final ButtonSetting autoClose;
    private final ButtonSetting debugMode;

    private boolean crafting = false;
    private boolean shouldOpenInventory = false;
    private int craftingStep = 0;
    private boolean keyWasPressed = false;
    private int craftDelayTicks = 0;

    // Slots da crafting grid
    private static final int CRAFT_RESULT_SLOT = 0;
    private static final int CRAFT_SLOT_1 = 1;
    private static final int CRAFT_SLOT_2 = 2;
    private static final int CRAFT_SLOT_3 = 3;

    private static final int INVENTORY_START = 9;
    private static final int INVENTORY_END = 44;

    // Salva slots originais dos ingredientes
    private int originalBowlSlot = -1;
    private int originalIngredient1Slot = -1;
    private int originalIngredient2Slot = -1;
    private boolean usingCocoaBeans = false;
    private boolean usingCactus = false;
    private boolean usingMelonSeeds = false;
    private boolean usingPumpkinSeeds = false;

    public Recraft() {
        super("Recraft", category.hg, "Crafta sopas de forma visível e automatizada");

        this.registerSetting(mode = new ModeSetting("Modo", new String[]{
                "Auto Open",
                "Manual"
        }, 1));
        this.registerSetting(craftSpeed = new SliderSetting("Velocidade", 20, 1, 40, 1));
        this.registerSetting(autoClose = new ButtonSetting("Auto Close", true));
        this.registerSetting(debugMode = new ButtonSetting("Debug", false));
    }

    @Override
    public void onEnable() {
        reset();
    }

    @Override
    public void onDisable() {
        if (autoClose.isToggled() && shouldOpenInventory && mc.currentScreen instanceof GuiInventory) {
            mc.thePlayer.closeScreen();
        }
        reset();
    }

    /** Retorna true enquanto o recraft está em andamento (AutoSoup deve pausar). */
    public boolean isCrafting() {
        return crafting;
    }

    private void reset() {
        crafting = false;
        shouldOpenInventory = false;
        craftingStep = 0;
        craftDelayTicks = 0;
        originalBowlSlot = -1;
        originalIngredient1Slot = -1;
        originalIngredient2Slot = -1;
        usingCocoaBeans = false;
        usingCactus = false;
        usingMelonSeeds = false;
        usingPumpkinSeeds = false;
    }

    @Override
    public void keybind() {
    }

    @SubscribeEvent
    public void onPreUpdate(PreUpdateEvent event) {
        if (!Utils.nullCheck()) return;

        // Não funciona com chat aberto
        if (mc.currentScreen instanceof GuiChat) {
            keyWasPressed = false;
            return;
        }

        // Detecta a tecla
        if (this.getKeycode() != 0) {
            boolean keyIsPressed = Keyboard.isKeyDown(this.getKeycode());
            
            if (mc.currentScreen instanceof GuiChat) {
                keyWasPressed = keyIsPressed;
                return;
            }
            
            if (keyIsPressed && !keyWasPressed && !crafting) {
                int modeIndex = (int) mode.getInput();

                if (modeIndex == 0) {
                    if (!(mc.currentScreen instanceof GuiInventory)) {
                        mc.displayGuiScreen(new GuiInventory(mc.thePlayer));
                        shouldOpenInventory = true;
                    }
                    startCrafting();
                } else {
                    if (mc.currentScreen instanceof GuiInventory) {
                        shouldOpenInventory = false;
                        startCrafting();
                    }
                }
            }
            
            keyWasPressed = keyIsPressed;
        }

        if (!crafting) return;

        if (!(mc.currentScreen instanceof GuiInventory)) {
            reset();
            return;
        }

        int speed = (int) craftSpeed.getInput();
        int delayNeeded = Math.max(0, (40 - speed) / 4);
        
        if (craftDelayTicks < delayNeeded) {
            craftDelayTicks++;
            return;
        }
        craftDelayTicks = 0;

        executeCraftingStep();
    }

    private void startCrafting() {
        // FORÇA o AutoSoup a parar completamente antes de começar
        if (ModuleManager.autoSoup != null && ModuleManager.autoSoup.isEnabled()) {
            ModuleManager.autoSoup.forceStop();
        }
        
        // Encontra o MAIOR STACK de cada ingrediente
        IngredientInfo bowls = findBiggestStack(Items.bowl);
        IngredientInfo cocoaBeans = findBiggestStack(Items.dye, 3);
        IngredientInfo cactus = findBiggestStack(Item.getItemFromBlock(Blocks.cactus));
        IngredientInfo melonSeeds = findBiggestStack(Items.melon_seeds);
        IngredientInfo pumpkinSeeds = findBiggestStack(Items.pumpkin_seeds);
        IngredientInfo redMushrooms = findBiggestStack(Item.getItemFromBlock(Blocks.red_mushroom));
        IngredientInfo brownMushrooms = findBiggestStack(Item.getItemFromBlock(Blocks.brown_mushroom));
        
        // Calcula quantas sopas podem ser feitas com CADA MAIOR STACK
        int soupsWithCocoa = cocoaBeans.size > 0 ? Math.min(bowls.size, cocoaBeans.size) : 0;
        int soupsWithCactus = cactus.size > 0 ? Math.min(bowls.size, cactus.size) : 0;
        int soupsWithMelon = melonSeeds.size > 0 ? Math.min(bowls.size, melonSeeds.size) : 0;
        int soupsWithPumpkin = pumpkinSeeds.size > 0 ? Math.min(bowls.size, pumpkinSeeds.size) : 0;
        int soupsWithMushrooms = (redMushrooms.size > 0 && brownMushrooms.size > 0) 
                ? Math.min(bowls.size, Math.min(redMushrooms.size, brownMushrooms.size)) : 0;
        
        if (debugMode.isToggled()) {
            Utils.sendMessage("§7Maior stack Bowls: " + bowls.size + " (slot " + bowls.slot + ")");
            Utils.sendMessage("§7Maior stack Cocoa: " + cocoaBeans.size + " §f→ faz §a" + soupsWithCocoa + " §fsopas");
            Utils.sendMessage("§7Maior stack Cactus: " + cactus.size + " §f→ faz §a" + soupsWithCactus + " §fsopas");
            Utils.sendMessage("§7Maior stack Melon Seeds: " + melonSeeds.size + " §f→ faz §a" + soupsWithMelon + " §fsopas");
            Utils.sendMessage("§7Maior stack Pumpkin Seeds: " + pumpkinSeeds.size + " §f→ faz §a" + soupsWithPumpkin + " §fsopas");
            Utils.sendMessage("§7Maior stack Mushrooms: R=" + redMushrooms.size + " B=" + brownMushrooms.size + " §f→ faz §a" + soupsWithMushrooms + " §fsopas");
        }
        
        // Escolhe o ingrediente com MAIOR STACK
        int maxSoups = Math.max(soupsWithCocoa, Math.max(soupsWithCactus, Math.max(soupsWithMelon, Math.max(soupsWithPumpkin, soupsWithMushrooms))));
        
        if (maxSoups == 0) {
            if (debugMode.isToggled()) {
                Utils.sendMessage("§cSem ingredientes!");
            }
            return;
        }
        
        usingCocoaBeans = false;
        usingCactus = false;
        usingMelonSeeds = false;
        usingPumpkinSeeds = false;

        if (soupsWithCocoa == maxSoups && soupsWithCocoa > 0) {
            usingCocoaBeans = true;
            originalBowlSlot = bowls.slot;
            originalIngredient1Slot = cocoaBeans.slot;
            originalIngredient2Slot = -1;
            
            if (debugMode.isToggled()) {
                Utils.sendMessage("§a✓ Usando Cocoa Beans (" + soupsWithCocoa + " sopas do maior stack)");
            }
        } else if (soupsWithCactus == maxSoups && soupsWithCactus > 0) {
            usingCactus = true;
            originalBowlSlot = bowls.slot;
            originalIngredient1Slot = cactus.slot;
            originalIngredient2Slot = -1;
            
            if (debugMode.isToggled()) {
                Utils.sendMessage("§a✓ Usando Cactus (" + soupsWithCactus + " sopas do maior stack)");
            }
        } else if (soupsWithMelon == maxSoups && soupsWithMelon > 0) {
            usingMelonSeeds = true;
            originalBowlSlot = bowls.slot;
            originalIngredient1Slot = melonSeeds.slot;
            originalIngredient2Slot = -1;
            
            if (debugMode.isToggled()) {
                Utils.sendMessage("§a✓ Usando Melon Seeds (" + soupsWithMelon + " sopas do maior stack)");
            }
        } else if (soupsWithPumpkin == maxSoups && soupsWithPumpkin > 0) {
            usingPumpkinSeeds = true;
            originalBowlSlot = bowls.slot;
            originalIngredient1Slot = pumpkinSeeds.slot;
            originalIngredient2Slot = -1;
            
            if (debugMode.isToggled()) {
                Utils.sendMessage("§a✓ Usando Pumpkin Seeds (" + soupsWithPumpkin + " sopas do maior stack)");
            }
        } else {
            originalBowlSlot = bowls.slot;
            originalIngredient1Slot = redMushrooms.slot;
            originalIngredient2Slot = brownMushrooms.slot;
            
            if (debugMode.isToggled()) {
                Utils.sendMessage("§a✓ Usando Cogumelos (" + soupsWithMushrooms + " sopas do maior stack)");
            }
        }

        if (originalBowlSlot == -1 || originalIngredient1Slot == -1) {
            if (debugMode.isToggled()) {
                Utils.sendMessage("§cErro ao encontrar slots!");
            }
            return;
        }

        if (!usingCocoaBeans && !usingCactus && !usingMelonSeeds && !usingPumpkinSeeds && originalIngredient2Slot == -1) {
            if (debugMode.isToggled()) {
                Utils.sendMessage("§cErro: sem cogumelo marrom!");
            }
            return;
        }

        crafting = true;
        craftingStep = 0;
        craftDelayTicks = 0;
        
        if (debugMode.isToggled()) {
            Utils.sendMessage("§aRecraft iniciado!");
        }
    }

    private IngredientInfo findBiggestStack(Item item) {
        Container container = mc.thePlayer.inventoryContainer;
        int biggestSlot = -1;
        int biggestSize = 0;
        
        for (int i = INVENTORY_START; i <= INVENTORY_END; i++) {
            Slot slot = container.getSlot(i);
            if (slot.getHasStack() && slot.getStack().getItem() == item) {
                if (slot.getStack().stackSize > biggestSize) {
                    biggestSize = slot.getStack().stackSize;
                    biggestSlot = i;
                }
            }
        }
        
        return new IngredientInfo(biggestSlot, biggestSize);
    }

    private IngredientInfo findBiggestStack(Item item, int metadata) {
        Container container = mc.thePlayer.inventoryContainer;
        int biggestSlot = -1;
        int biggestSize = 0;
        
        for (int i = INVENTORY_START; i <= INVENTORY_END; i++) {
            Slot slot = container.getSlot(i);
            if (slot.getHasStack() && slot.getStack().getItem() == item && slot.getStack().getMetadata() == metadata) {
                if (slot.getStack().stackSize > biggestSize) {
                    biggestSize = slot.getStack().stackSize;
                    biggestSlot = i;
                }
            }
        }
        
        return new IngredientInfo(biggestSlot, biggestSize);
    }

    private void executeCraftingStep() {
        Container container = mc.thePlayer.inventoryContainer;

        switch (craftingStep) {
            case 0: // Move bowls
                moveHalfToSlot(originalBowlSlot, CRAFT_SLOT_1);
                craftingStep++;
                break;

            case 1: // Move ingrediente 1
                moveHalfToSlot(originalIngredient1Slot, CRAFT_SLOT_2);
                craftingStep++;
                break;

            case 2: // Move ingrediente 2 (só para cogumelos)
                if (originalIngredient2Slot != -1) {
                    moveHalfToSlot(originalIngredient2Slot, CRAFT_SLOT_3);
                }
                craftingStep++;
                break;

            case 3: // Crafta sopas
                craftAllSoups();
                craftingStep++;
                break;

            case 4: // Devolve ingredientes
                returnIngredientsToOriginalSlots();
                craftingStep++;
                break;

            case 5: // Finaliza
                if (autoClose.isToggled() && shouldOpenInventory) {
                    mc.thePlayer.closeScreen();
                }
                reset();
                break;
        }
    }

    private void moveHalfToSlot(int fromSlot, int toSlot) {
        if (fromSlot == -1) return;
        
        Container container = mc.thePlayer.inventoryContainer;
        
        // Click direito = pega metade
        mc.playerController.windowClick(container.windowId, fromSlot, 1, 0, mc.thePlayer);
        // Click esquerdo = solta
        mc.playerController.windowClick(container.windowId, toSlot, 0, 0, mc.thePlayer);
    }

    private void craftAllSoups() {
        Container container = mc.thePlayer.inventoryContainer;
        int crafted = 0;
        
        for (int i = 0; i < 64; i++) {
            Slot resultSlot = container.getSlot(CRAFT_RESULT_SLOT);
            
            if (resultSlot.getHasStack() && resultSlot.getStack().getItem() == Items.mushroom_stew) {
                mc.playerController.windowClick(container.windowId, CRAFT_RESULT_SLOT, 0, 1, mc.thePlayer);
                crafted++;
            } else {
                break;
            }
        }
        
        if (debugMode.isToggled() && crafted > 0) {
            Utils.sendMessage("§aCraftadas: " + crafted + " sopas");
        }
    }

    private void returnIngredientsToOriginalSlots() {
        Container container = mc.thePlayer.inventoryContainer;
        
        // Devolve bowls
        Slot craftSlot1 = container.getSlot(CRAFT_SLOT_1);
        if (craftSlot1.getHasStack() && originalBowlSlot != -1) {
            mc.playerController.windowClick(container.windowId, CRAFT_SLOT_1, 0, 0, mc.thePlayer);
            mc.playerController.windowClick(container.windowId, originalBowlSlot, 0, 0, mc.thePlayer);
        }
        
        // Devolve ingrediente 1
        Slot craftSlot2 = container.getSlot(CRAFT_SLOT_2);
        if (craftSlot2.getHasStack() && originalIngredient1Slot != -1) {
            mc.playerController.windowClick(container.windowId, CRAFT_SLOT_2, 0, 0, mc.thePlayer);
            mc.playerController.windowClick(container.windowId, originalIngredient1Slot, 0, 0, mc.thePlayer);
        }
        
        // Devolve ingrediente 2 (só cogumelos)
        if (originalIngredient2Slot != -1) {
            Slot craftSlot3 = container.getSlot(CRAFT_SLOT_3);
            if (craftSlot3.getHasStack() && originalIngredient2Slot != -1) {
                mc.playerController.windowClick(container.windowId, CRAFT_SLOT_3, 0, 0, mc.thePlayer);
                mc.playerController.windowClick(container.windowId, originalIngredient2Slot, 0, 0, mc.thePlayer);
            }
        }
    }

    // Classe helper
    private static class IngredientInfo {
        int slot;
        int size;
        
        IngredientInfo(int slot, int size) {
            this.slot = slot;
            this.size = size;
        }
    }

    @Override
    public String getPrettyInfo() {
        String[] modes = {"Auto", "Manual"};
        int index = (int) mode.getInput();
        return index >= 0 && index < modes.length ? modes[index] : "";
    }
}