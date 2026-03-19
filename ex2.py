


class GringottsController:

    def __init__(self, map_shape, harry_loc, initial_observations):
        # Timeout: 60 seconds
        self.counter = 0
        self.m = map_shape[0]  # num rows
        self.n = map_shape[1]  # num columns
        self.max_steps = 5 + 3 * (self.m + self.n)  # maximum number of rounds
        self.current_place = harry_loc
        self.last_place = None  # New attribute to track the last visited tile
        self.variables = {}
        self.actions = {}
        self.harry_initial_loc = harry_loc
        self.detected_dragons = set()  # set of dragons detected in the game
        self.suspected_traps_by_tile = {}
        self.generate_variables(initial_observations)  # initialize the variables including the initial and goal variables

    def create_variable(self, name, state, direction, vaults, dragons, i, j):
        """
        יוצר משתנה עם שם ייחודי ותווית זמן.
        """
        full_name = f"{name}"
        self.variables[full_name] = False

        if state == "safe":
            if direction == "up":
                if 0 <= i - 1:
                    self.variables[full_name] = True
            elif direction == "down":
                if i + 1 <= self.m - 1:
                    self.variables[full_name] = True
            elif direction == "left":
                if j - 1 >= 0:
                    self.variables[full_name] = True
            else:
                if j + 1 <= self.n - 1:
                    self.variables[full_name] = True
        elif state == "harry":
            if (i, j) == self.harry_initial_loc:
                self.variables[full_name] = True
        elif state == "dragon":
            if (i, j) in dragons:
                self.variables[full_name] = True
        elif state == "trap":
            # במשבצת ההתחלתית, trap מוגדר כ-False
            self.variables[full_name] = False
        elif state == "suspected_trap":
            # במשבצת ההתחלתית, suspected_trap מוגדר כ-False
            if (i, j) == self.harry_initial_loc:
                self.variables[full_name] = False
            else:
                self.variables[full_name] = True
        elif state == "vault":
            if (i, j) in vaults:
                self.variables[full_name] = True
        elif state == "checked_vault":
            self.variables[full_name] = False
        elif state == "visited":
            if (i, j) == self.harry_initial_loc:
                self.variables[full_name] = True
        elif state == "score":
            self.variables[full_name] = 4  # מקסימום ניקוד למשבצת
            if not (0 <= i - 1):
                self.variables[full_name] -= 1
            if not (i + 1 <= self.m - 1):
                self.variables[full_name] -= 1
            if not (j - 1 >= 0):
                self.variables[full_name] -= 1
            if not (j + 1 <= self.n - 1):
                self.variables[full_name] -= 1
            if self.variables[f"dragon(Tile_{i}_{j})"]:
                self.variables[full_name] = float('-inf')  # ניקוד מינימלי למשבצת עם דרקון

    def create_action(self, name):
        """
        יוצר משתנה פעולה עם שם ייחודי ותווית זמן.
        """
        full_name = f"{name}"
        self.actions[full_name] = False

    def generate_variables(self, initial_observations):
        """
        מייצר את כל המשתנים האפשריים עבור כל אריח בלוח ולכל שלב זמן.
        """
        vaults = []  # רשימה לתיבות
        dragons = []  # רשימה לדרקונים
        flag_Sulfur = False

        # איסוף תצפיות ראשוניות
        if initial_observations:
            for obs in initial_observations:
                obs_type = obs[0]
                if obs_type == 'vault':
                    obs_loc=obs[1]
                    vaults.append(obs_loc)
                elif obs_type == 'dragon':
                    obs_loc=obs[1]
                    dragons.append(obs_loc)
                elif obs_type == 'sulfur':
                    flag_Sulfur = True

        # יצירת משתנים
        for i in range(self.m):
            for j in range(self.n):
                for direction in ["up", "down", "left", "right"]:
                    self.create_variable(f"safe(Tile_{i}_{j}, {direction})", "safe", direction, vaults, dragons, i, j)
                self.create_variable(f"trap(Tile_{i}_{j})", "trap", None, vaults, dragons, i, j)
                self.create_variable(f"dragon(Tile_{i}_{j})", "dragon", None, vaults, dragons, i, j)
                self.create_variable(f"vault(Tile_{i}_{j})", "vault", None, vaults, dragons, i, j)
                self.create_variable(f"checked_vault(Tile_{i}_{j})", "checked_vault", None, vaults, dragons, i, j)
                self.create_variable(f"harry(Tile_{i}_{j})", "harry", None, vaults, dragons, i, j)
                self.create_variable(f"visited(Tile_{i}_{j})", "visited", None, vaults, dragons, i, j)
                self.create_variable(f"score(Tile_{i}_{j})", "score", None, vaults, dragons, i, j)
                self.create_variable(f"suspected_trap(Tile_{i}_{j})", "suspected_trap", None, vaults, dragons, i, j)

        # עדכון לפי דרקונים ותיבות
        self.trap_Update(flag_Sulfur)
        if dragons:
            for dragon in dragons:
                self.update_score(dragon)


    def trap_Update(self,flag_Sulfur):
        x, y = self.current_place  # the location we smelled the sulfur

        # אם אין גופרית, המשבצות מסביב לא יכולות להיות מלכודות
        if not flag_Sulfur:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.m and 0 <= ny < self.n:
                    self.variables[f"suspected_trap(Tile_{nx}_{ny})"] = False

        # אם כן ריח גופרית, שמור את כל הסביבה כרשימת חשודים
        else:
            self.suspected_traps_by_tile[(x, y)] = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.m and 0 <= ny < self.n:
                    self.suspected_traps_by_tile[(x, y)].append((nx, ny))

        # ניתוח רשימות החשודים
        for key, suspects in list(self.suspected_traps_by_tile.items()):#TODO: check if it works well
            # הסר משבצות שלא יכולות להיות מלכודות
            self.suspected_traps_by_tile[key] = [tile for tile in suspects if
                                                 self.variables[f"suspected_trap(Tile_{tile[0]}_{tile[1]})"]]

            # אם נשאר רק חשוד אחד, הוא מלכודת
            if len(self.suspected_traps_by_tile[key]) == 1:#key is the location we smelled the sulfur and suspect is the tile we think might be with a trap
                trap_tile = self.suspected_traps_by_tile[key][0]
                self.variables[f"trap(Tile_{trap_tile[0]}_{trap_tile[1]})"] = True
                self.variables[f"suspected_trap(Tile_{trap_tile[0]}_{trap_tile[1]})"] = False
                del self.suspected_traps_by_tile[key]

    def dragon_Update(self, dragon_loc):
        """
        update new dragons discoveres
        dragon_loc is the new location we discovered and delivered to this function
        t is the timestamp of the discovery
        """
        i = dragon_loc[0]
        j = dragon_loc[1]
        self.variables[f"dragon(Tile_{i}_{j})"] = True
        self.variables[f"score(Tile_{i}_{j})"]=float('-inf')

    def vault_Update(self, vault_loc):
        """
        update new dragons discoveres
        dragon_loc is the new location we discovered and delivered to this function
        t is the timestamp of the discovery
        """
        i = vault_loc[0]
        j = vault_loc[1]
        self.variables[f"vault(Tile_{i}_{j})"] = True

    def checked_vault_Update(self, vault_loc):
        """
        update that we checked that vault in order to prevent double checks in the same vault
        """
        i = vault_loc[0]
        j = vault_loc[1]
        self.variables[f"visited(Tile_{i}_{j})"] = True
        self.variables[f"checked_vault(Tile_{i}_{j})"] = True

    def harry_Update(self, harry_new_loc):
        """
        Update Harry's current location and the last place.
        also update the current tile's score
        """
        harry_old_loc = self.current_place
        self.last_place = harry_old_loc  # Track the last place
        x_old = harry_old_loc[0]
        y_old = harry_old_loc[1]
        i = harry_new_loc[0]
        j = harry_new_loc[1]
        self.current_place = harry_new_loc
        self.variables[f"harry(Tile_{x_old}_{y_old})"] = False
        self.variables[f"harry(Tile_{i}_{j})"] = True
        self.variables[f"visited(Tile_{i}_{j})"] = True
        self.variables[f"score(Tile_{i}_{j})"] = self.variables[f"score(Tile_{i}_{j})"]-1 #update our current tile score



    def destroy_trap(self, trap_loc):
        """
        destroy a trap in trap_loc
        """
        i = trap_loc[0]
        j = trap_loc[1]
        self.variables[f"suspected_trap(Tile_{i}_{j})"] = False
        self.variables[f"trap(Tile_{i}_{j})"] = False

    def get_possible_actions(self):
        """
        Returns all possible legal actions from current location with improved safety checks.
        Never returns wait action.
        """
        possible_actions = []
        curr_x, curr_y = self.current_place

        # Check if we can collect from current location
        if self.variables[f"vault(Tile_{curr_x}_{curr_y})"] and not self.variables[
            f"checked_vault(Tile_{curr_x}_{curr_y})"]:
            possible_actions.append(("collect",))

        # Check possible moves in all directions
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:  # right, left, down, up
            new_x, new_y = curr_x + dx, curr_y + dy

            # Check if move is within bounds
            if 0 <= new_x < self.m and 0 <= new_y < self.n:
                # Skip if we know there's a dragon
                if self.variables[f"dragon(Tile_{new_x}_{new_y})"]:
                    continue

                # If there's a trap or suspected trap, offer destroy action
                if self.variables[f"suspected_trap(Tile_{new_x}_{new_y})"] or self.variables[
                    f"trap(Tile_{new_x}_{new_y})"]:
                    possible_actions.append(("destroy", (new_x, new_y)))
                else:
                    # Only add move action if we're certain it's safe
                    possible_actions.append(("move", (new_x, new_y)))

        return possible_actions


    def get_direction_to_nearest_unvisited_vault(self, x, y):
        """
        Returns the direction to move towards the nearest unvisited tile
        while avoiding the last visited tile.
        """
        min_distance = float('inf')
        vault = None

        # First, try to find unchecked vaults
        for i in range(self.m):
            for j in range(self.n):
                if (self.variables[f"vault(Tile_{i}_{j})"] and
                        not self.variables[f"checked_vault(Tile_{i}_{j})"]):
                    distance = abs(x - i) + abs(y - j)
                    if distance < min_distance:
                        min_distance = distance
                        vault = (i, j)

        if vault is None:
            return None

        # Find the best immediate move towards the target while avoiding the last place
        curr_x, curr_y = x, y
        target_x, target_y = vault

        possible_next_moves = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_x, new_y = curr_x + dx, curr_y + dy
            if 0 <= new_x < self.m and 0 <= new_y < self.n:
                # Only consider moves that don't lead to known dangers
                if not self.variables[f"dragon(Tile_{new_x}_{new_y})"] :
                    new_distance = abs(new_x - target_x) + abs(new_y - target_y) - self.variables[f"score(Tile_{new_x}_{new_y})"]#changed- minimize the score and distance
                    possible_next_moves.append(((new_x, new_y), new_distance))

        if possible_next_moves:
            return min(possible_next_moves, key=lambda x: x[1])[0]
        return None

    def update_score(self, dragon=None):
        """
        Update the score of tiles:
        If a dragon is provided, reduce scores of its neighbors.
        Otherwise, scan neighbors of the current tile and reduce scores of their visited neighbors.
        """
        if dragon:  # If a dragon's coordinates are provided
            if dragon in self.detected_dragons:  # We have already detected this dragon
                return

            self.detected_dragons.add(dragon)
            x, y = dragon

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:  # Loop over all neighbors
                nx, ny = x + dx, y + dy  # Coordinates of the current tile we update

                if 0 <= nx < self.m and 0 <= ny < self.n:  # Check bounds
                    # Reduce the score of the tile by 1
                    self.variables[f"score(Tile_{nx}_{ny})"] -= 1

                    # If the tile is unvisited and the score drops to 1 or lower, mark it as undesirable
                    if self.variables[f"score(Tile_{nx}_{ny})"] <= 1 and not self.variables[f"visited(Tile_{nx}_{ny})"]:
                        self.variables[f"score(Tile_{nx}_{ny})"] = float('-inf')

    def get_next_action(self, observations):
        """
        Decide next action based on current state and observations.
        Never returns wait action.
        """
        # Update knowledge base from observations
        vaults = []
        dragons = []
        flag_Sulfur = False
        if observations:
            for obs in observations:
                obs_type = obs[0]
                if obs_type == 'vault':
                    vaults.append(obs[1])
                    self.vault_Update(obs[1])
                elif obs_type == 'dragon':
                    dragons.append(obs[1])
                    self.dragon_Update(obs[1])
                    self.update_score(obs[1])  #update each tile that is near a dragon
                elif obs_type == 'sulfur':
                    flag_Sulfur = True

        self.trap_Update(flag_Sulfur)#update the traps state after an observation
        if dragons:
            for dragon in dragons:
                self.update_score(dragon)
        # Get current possible actions
        possible_actions = self.get_possible_actions()
        if not possible_actions:
            return ('wait', )#if there is no option then wait
        # if not possible_actions:
        #     print(("wait", self.current_place))
        #     return "wait", self.current_place  # Stay in place if no other options

        # Priority 1: Collect if at vault
        if ("collect",) in possible_actions:
            self.checked_vault_Update(self.current_place)
            #print(("collect",))
            return "collect",

        # Priority 2: Move to the best adjacent unchecked vault
        unchecked_vault_actions = [action for action in possible_actions
                                   if action[0] in ["move", "destroy"] and
                                   self.variables[f"vault(Tile_{action[1][0]}_{action[1][1]})"] and
                                   not self.variables[f"checked_vault(Tile_{action[1][0]}_{action[1][1]})"]]

        if unchecked_vault_actions:
            # בחר את הכספת עם הציון הטוב ביותר
            best_vault = self.next_tile(unchecked_vault_actions,True)
            if best_vault:
                for action in unchecked_vault_actions:
                    if action[1] == best_vault:
                        if action[0] == "move":
                            self.harry_Update(best_vault)
                            #print(action)
                            return action
                        elif action[0] == "destroy":
                            self.destroy_trap(best_vault)
                            #print(action, "1")
                            return action

        # Priority 3: Move towards nearest unvisited vault
        next_target_to_vault = self.get_direction_to_nearest_unvisited_vault(self.current_place[0], self.current_place[1])
        if next_target_to_vault:
            for action in possible_actions:
                if action[0] == "move" and action[1] == next_target_to_vault:
                    self.harry_Update(next_target_to_vault)
                    #print(action, "*")
                    return action
                elif action[0] == "destroy" and action[1] == next_target_to_vault:
                    self.destroy_trap(action[1])
                    #print(action, "2")
                    return action

        #priority 4: Move towards the new best tile possible with the scoring rule:
        next_best_tile = self.next_tile(possible_actions,False)
        if next_best_tile:
            for action in possible_actions:
                if action[0] == "move" and action[1] == next_best_tile:
                    self.harry_Update(next_best_tile)
                    #print(action, "*")
                    return action
                elif action[0] == "destroy" and action[1] == next_best_tile:
                    self.destroy_trap(action[1])
                    #print(action, "2")
                    return action

    def next_tile(self, possible_actions, vaults_comparison):
        """
        Choose the next best tile to move or destroy.
        If a real trap is identified, prioritize the tile with the trap for destruction.
        If all surrounding tiles are visited or Dead Ends, find the best distant tile to target
        and take the best immediate step towards it.
        Returns the coordinates (x, y) of the next tile.
        """
        best_tile = None
        best_score = float('-inf')
        all_visited = True  # Flag to check if all surrounding tiles are visited

        # Case 1: Compare vaults
        if vaults_comparison:
            for action in possible_actions:
                action_type, coords = action
                x, y = coords
                current_score = self.variables[f"score(Tile_{x}_{y})"]
                if current_score >= best_score:  # Include the case we have a vault in a dead-end tile
                    best_score = current_score
                    best_tile = (x, y)
            return best_tile

        # Case 2: Check for real traps and prioritize them
        for action in possible_actions:
            action_type, coords = action
            x, y = coords
            if action_type == "destroy" and self.variables[f"trap(Tile_{x}_{y})"]:
                # Prioritize the real trap's tile for destruction
                return (x, y)

        # Case 3: If all surrounding tiles are visited, find the best distant unvisited tile
        for action in possible_actions:
            action_type, coords = action
            x, y = coords
            if not self.variables[f"visited(Tile_{x}_{y})"]:  # If a tile isn't visited, update the flag
                all_visited = False

        if all_visited:
            best_distant_tile = None
            min_distant_score = float('inf')
            current_x, current_y = self.current_place

            # Step 1: Find the best distant unvisited tile
            for i in range(self.m):
                for j in range(self.n):
                    # Skip tiles with dragons or already visited
                    if self.variables[f"dragon(Tile_{i}_{j})"] or self.variables[f"visited(Tile_{i}_{j})"]:
                        continue

                    distant_score = abs(current_x - i) + abs(current_y - j) - self.variables[f"score(Tile_{i}_{j})"]


                    if distant_score < min_distant_score:
                        min_distant_score = distant_score
                        best_distant_tile = (i, j)

            # Step 2: Find the best immediate step towards the distant tile
            if best_distant_tile:
                target_x, target_y = best_distant_tile
                min_distance = float('inf')

                for action in possible_actions:
                    action_type, coords = action
                    x, y = coords
                    # Calculate the distance to the target
                    distance_to_target = abs(x - target_x) + abs(y - target_y)

                    if distance_to_target < min_distance:
                        min_distance = distance_to_target
                        best_tile = (x, y)

        # Case 4: Check for best scoring tiles if no real traps are found and at least one tile isn't visited
        if best_tile is None:
            for action in possible_actions:
                action_type, coords = action
                x, y = coords
                current_score = self.variables[f"score(Tile_{x}_{y})"]
                if current_score > best_score:
                    best_score = current_score
                    best_tile = (x, y)

        return best_tile



