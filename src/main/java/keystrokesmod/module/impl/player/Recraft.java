package keystrokesmod.module.impl.player;

import keystrokesmod.event.PreUpdateEvent;
import keystrokesmod.module.Module;
import keystrokesmod.module.setting.impl.ButtonSetting;
import keystrokesmod.module.setting.impl.DescriptionSetting;
import keystrokesmod.module.setting.impl.ModeSetting;
import keystrokesmod.module.setting.impl.SliderSetting;
import keystrokesmod.utility.Utils;
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
    private DescriptionSetting info;

    private boolean crafting = false;
    private boolean shouldOpenInventory = false;
    private int craftingStep = 0;
    private boolean keyWasPressed = false;
    private int craftDelayTicks = 0;

    // Slots da crafting grid no inventário (2x2)
    private static final int CRAFT_RESULT_SLOT = 0;
    private static final int CRAFT_SLOT_1 = 1; // top-left (bowl)
    private static final int CRAFT_SLOT_2 = 2; // top-right (ingrediente)
    private static final int CRAFT_SLOT_3 = 3; // bottom-left (ingrediente 2 - só para cogumelos)

    // Slots do inventário do jogador
    private static final int INVENTORY_START = 9;
    private static final int INVENTORY_END = 44;

    private int savedBowlSlot = -1;
    private int savedIngredient1Slot = -1;
    private int savedIngredient2Slot = -1;
    private boolean usingCocoaBeans = false;

    public Recraft() {
        super("Recraft", category.hg, "Crafta sopas de forma visível e automatizada");

        this.registerSetting(info = new DescriptionSetting("§7Aperte a tecla para iniciar o recraft"));
        this.registerSetting(mode = new ModeSetting("Modo", new String[]{
                "Auto Open", // Aperta tecla -> abre inv -> crafta -> fecha
                "Manual"     // Inv aberto -> aperta tecla -> crafta
        }, 1));
        this.registerSetting(craftSpeed = new SliderSetting("Velocidade", 20, 1, 40, 1));
        this.registerSetting(autoClose = new ButtonSetting("Auto Close", true));
        this.registerSetting(debugMode = new ButtonSetting("Debug", false));
    }

    @Override
    public void onEnable() {
        crafting = false;
        shouldOpenInventory = false;
        craftingStep = 0;
    }

    @Override
    public void onDisable() {
        if (autoClose.isToggled() && shouldOpenInventory && mc.currentScreen instanceof GuiInventory) {
            mc.thePlayer.closeScreen();
        }
        crafting = false;
        shouldOpenInventory = false;
        craftingStep = 0;
    }

    @Override
    public void keybind() {
        // Este método não é usado mais, movemos a lógica para onPreUpdate
    }

    private void startCrafting() {
        crafting = true;
        craftingStep = 0;

        // Encontra os slots dos ingredientes e decide qual usar
        savedBowlSlot = findItemSlot(Items.bowl);
        
        // Verifica cocoa beans vs cogumelos
        int cocoaBeansSlot = findItemSlot(Items.dye, 3); // Cocoa beans é dye com metadata 3
        int cocoaBeansCount = cocoaBeansSlot != -1 ? getItemCount(cocoaBeansSlot) : 0;
        
        int redMushroomSlot = findItemSlot(Item.getItemFromBlock(Blocks.red_mushroom));
        int redMushroomCount = redMushroomSlot != -1 ? getItemCount(redMushroomSlot) : 0;
        
        int brownMushroomSlot = findItemSlot(Item.getItemFromBlock(Blocks.brown_mushroom));
        int brownMushroomCount = brownMushroomSlot != -1 ? getItemCount(brownMushroomSlot) : 0;
        
        // Calcula qual tem mais ingredientes
        int mushroomTotal = Math.min(redMushroomCount, brownMushroomCount);
        
        if (cocoaBeansCount > mushroomTotal) {
            // Usa Cocoa Beans - APENAS 2 INGREDIENTES
            usingCocoaBeans = true;
            savedIngredient1Slot = cocoaBeansSlot;
            savedIngredient2Slot = -1; // NÃO USA O TERCEIRO SLOT
            
            if (debugMode.isToggled()) {
                Utils.sendMessage("§aUsando Cocoa Beans (" + cocoaBeansCount + " disponíveis)");
            }
        } else {
            // Usa Cogumelos - 3 INGREDIENTES
            usingCocoaBeans = false;
            savedIngredient1Slot = redMushroomSlot;
            savedIngredient2Slot = brownMushroomSlot;
            
            if (debugMode.isToggled()) {
                Utils.sendMessage("§aUsando Cogumelos (" + mushroomTotal + " sets disponíveis)");
            }
        }

        if (savedBowlSlot == -1 || savedIngredient1Slot == -1) {
            if (debugMode.isToggled()) {
                Utils.sendMessage("§cSem ingredientes suficientes para craftar!");
            }
            crafting = false;
            return;
        }

        // Verifica ingrediente 2 (só necessário para cogumelos)
        if (!usingCocoaBeans && savedIngredient2Slot == -1) {
            if (debugMode.isToggled()) {
                Utils.sendMessage("§cSem cogumelos marrons suficientes!");
            }
            crafting = false;
            return;
        }

        if (debugMode.isToggled()) {
            Utils.sendMessage("§aRecraft iniciado!");
        }
    }

    private int getItemCount(int slotIndex) {
        if (slotIndex == -1) return 0;
        Container container = mc.thePlayer.inventoryContainer;
        Slot slot = container.getSlot(slotIndex);
        if (slot.getHasStack()) {
            return slot.getStack().stackSize;
        }
        return 0;
    }

    @SubscribeEvent
    public void onPreUpdate(PreUpdateEvent event) {
        if (!Utils.nullCheck()) return;

        // Detecta a tecla sendo pressionada
        if (this.getKeycode() != 0) {
            boolean keyIsPressed = Keyboard.isKeyDown(this.getKeycode());
            
            if (keyIsPressed && !keyWasPressed && !crafting) {
                // Tecla foi pressionada (borda de subida)
                int modeIndex = (int) mode.getInput();

                if (modeIndex == 0) { // Auto Open
                    if (!(mc.currentScreen instanceof GuiInventory)) {
                        mc.displayGuiScreen(new GuiInventory(mc.thePlayer));
                        shouldOpenInventory = true;
                    }
                    startCrafting();
                } else { // Manual
                    if (mc.currentScreen instanceof GuiInventory) {
                        shouldOpenInventory = false;
                        startCrafting();
                    } else {
                        if (debugMode.isToggled()) {
                            Utils.sendMessage("§cAbra o inventário primeiro!");
                        }
                    }
                }
            }
            
            keyWasPressed = keyIsPressed;
        }

        if (!crafting) return;

        // Verifica se o inventário foi fechado
        if (!(mc.currentScreen instanceof GuiInventory)) {
            crafting = false;
            if (debugMode.isToggled()) {
                Utils.sendMessage("§cRecraft cancelado - inventário fechado");
            }
            return;
        }

        // Sistema de delay baseado na velocidade
        // Velocidade 1 = mais lento (10 ticks de delay)
        // Velocidade 40 = instantâneo (0 ticks de delay)
        int speed = (int) craftSpeed.getInput();
        int delayNeeded = Math.max(0, (40 - speed) / 4);
        
        if (craftDelayTicks < delayNeeded) {
            craftDelayTicks++;
            return;
        }
        craftDelayTicks = 0;

        // Executa o passo atual do crafting
        executeCraftingStep();
    }

    private void executeCraftingStep() {
        Container container = mc.thePlayer.inventoryContainer;

        switch (craftingStep) {
            case 0: // Pega METADE dos bowls e coloca no slot 1
                if (savedBowlSlot != -1) {
                    Slot bowlSlot = container.getSlot(savedBowlSlot);
                    if (bowlSlot.getHasStack()) {
                        // Click DIREITO = pega metade automaticamente
                        mc.playerController.windowClick(container.windowId, savedBowlSlot, 1, 0, mc.thePlayer);
                        // Click ESQUERDO = solta tudo
                        mc.playerController.windowClick(container.windowId, CRAFT_SLOT_1, 0, 0, mc.thePlayer);
                        
                        if (debugMode.isToggled()) {
                            Utils.sendMessage("§7Bowls colocados no craft");
                        }
                    }
                }
                craftingStep++;
                break;

            case 1: // Pega METADE do ingrediente 1
                if (savedIngredient1Slot != -1) {
                    Slot ingredient1Slot = container.getSlot(savedIngredient1Slot);
                    if (ingredient1Slot.getHasStack()) {
                        // Click DIREITO = pega metade
                        mc.playerController.windowClick(container.windowId, savedIngredient1Slot, 1, 0, mc.thePlayer);
                        // Click ESQUERDO = solta tudo
                        mc.playerController.windowClick(container.windowId, CRAFT_SLOT_2, 0, 0, mc.thePlayer);
                        
                        if (debugMode.isToggled()) {
                            String ingredientName = usingCocoaBeans ? "Cocoa Beans" : "Cogumelos Vermelhos";
                            Utils.sendMessage("§7" + ingredientName + " colocados no craft");
                        }
                    }
                }
                craftingStep++;
                break;

            case 2: // Pega METADE do ingrediente 2 (APENAS PARA COGUMELOS)
                if (!usingCocoaBeans && savedIngredient2Slot != -1) {
                    Slot ingredient2Slot = container.getSlot(savedIngredient2Slot);
                    if (ingredient2Slot.getHasStack()) {
                        // Click DIREITO = pega metade
                        mc.playerController.windowClick(container.windowId, savedIngredient2Slot, 1, 0, mc.thePlayer);
                        // Click ESQUERDO = solta tudo
                        mc.playerController.windowClick(container.windowId, CRAFT_SLOT_3, 0, 0, mc.thePlayer);
                        
                        if (debugMode.isToggled()) {
                            Utils.sendMessage("§7Cogumelos Marrons colocados no craft");
                        }
                    }
                } else if (usingCocoaBeans) {
                    // Cocoa beans não usa terceiro ingrediente, pula direto
                    if (debugMode.isToggled()) {
                        Utils.sendMessage("§7Cocoa Beans - pulando slot 3");
                    }
                }
                craftingStep++;
                break;

            case 3: // Crafta as sopas
                craftAllSoups(container);
                craftingStep++;
                break;

            case 4: // Pega ingredientes que sobraram antes de fechar
                collectLeftoverIngredients(container);
                craftingStep++;
                break;

            case 5: // Finaliza
                crafting = false;
                
                if (debugMode.isToggled()) {
                    Utils.sendMessage("§aRecraft finalizado!");
                }

                // Fecha o inventário se foi aberto automaticamente
                if (autoClose.isToggled() && shouldOpenInventory) {
                    mc.thePlayer.closeScreen();
                }
                shouldOpenInventory = false;
                break;
        }
    }

    private void craftAllSoups(Container container) {
        // Verifica se tem espaço no inventário
        if (!hasInventorySpace(container)) {
            if (debugMode.isToggled()) {
                Utils.sendMessage("§cInventário cheio! Limpe espaço antes de craftar.");
            }
            collectLeftoverIngredients(container);
            crafting = false;
            return;
        }

        int soupsCrafted = 0;
        
        // Crafta TODAS as sopas de uma vez
        for (int i = 0; i < 64; i++) {
            Slot resultSlot = container.getSlot(CRAFT_RESULT_SLOT);
            
            if (resultSlot.getHasStack() && resultSlot.getStack().getItem() == Items.mushroom_stew) {
                // Shift+Click para pegar a sopa
                mc.playerController.windowClick(container.windowId, CRAFT_RESULT_SLOT, 0, 1, mc.thePlayer);
                soupsCrafted++;
            } else {
                break;
            }
        }
        
        if (debugMode.isToggled() && soupsCrafted > 0) {
            Utils.sendMessage("§aSopas craftadas: §f" + soupsCrafted);
        }
    }

    private void collectLeftoverIngredients(Container container) {
        // Pega de volta os ingredientes que sobraram na crafting grid
        for (int slot = CRAFT_SLOT_1; slot <= CRAFT_SLOT_3; slot++) {
            Slot craftSlot = container.getSlot(slot);
            if (craftSlot.getHasStack()) {
                // Shift+Click para mover para o inventário
                mc.playerController.windowClick(container.windowId, slot, 0, 1, mc.thePlayer);
                
                if (debugMode.isToggled()) {
                    Utils.sendMessage("§7Ingredientes sobrou coletados do slot " + slot);
                }
            }
        }
    }

    private boolean hasInventorySpace(Container container) {
        for (int i = INVENTORY_START; i <= INVENTORY_END; i++) {
            Slot slot = container.getSlot(i);
            if (!slot.getHasStack()) {
                return true;
            }
            if (slot.getStack().getItem() == Items.mushroom_stew && slot.getStack().stackSize < 64) {
                return true;
            }
        }
        return false;
    }

    private int findItemSlot(Item item) {
        Container container = mc.thePlayer.inventoryContainer;
        
        for (int i = INVENTORY_START; i <= INVENTORY_END; i++) {
            Slot slot = container.getSlot(i);
            if (slot.getHasStack() && slot.getStack().getItem() == item) {
                return i;
            }
        }
        return -1;
    }

    private int findItemSlot(Item item, int metadata) {
        Container container = mc.thePlayer.inventoryContainer;
        
        for (int i = INVENTORY_START; i <= INVENTORY_END; i++) {
            Slot slot = container.getSlot(i);
            if (slot.getHasStack() && slot.getStack().getItem() == item && slot.getStack().getMetadata() == metadata) {
                return i;
            }
        }
        return -1;
    }

    @Override
    public String getPrettyInfo() {
        String[] modes = {"Auto", "Manual"};
        int index = (int) mode.getInput();
        return index >= 0 && index < modes.length ? modes[index] : "";
    }
}
