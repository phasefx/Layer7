# Online Raffle

The program: a simple bouncer for a small online raffle.

- Take a list of ticket entries, each with a name and a number of tickets bought.
- Reject the whole batch up front if any single entry bought more than 100 tickets (anti-abuse rule) — this should be a hard stop, nothing further runs.
- Otherwise, weight each entry by ticket count and pick a winner at random.
- If there are fewer than 2 unique entrants, skip the drawing entirely and report "not enough entrants" instead of picking a winner.
- Otherwise, announce the winner and also report the total number of tickets in play.

Allow exception: 9 sub-headers

Though I think I'm going to come in at 7 now.

## A Ticket

- Take a list of ticket entries, each with a name and a number of tickets bought.

Okay, let's describe what a ticket might look like:

```JSON
    { "name": "", "tickets_bought": 0 }
```

If I ever want to reference this else, A_Ticket or `A Ticket` should probably be enough. However, if needed, we can start qualifying it using filenames and nested headers as an address space.

Online_Raffle.A_Ticket, or if that wasn't clear enough, then raffle.md-Online_Raffle.A_Ticket.

Our headers are referenceable as identifiers.

## The Tickets

So this is going to be an array to hold entries shaped like A_Ticket. We don't need to type it; I'm not one to reach for typed languages,
And I can't think of an intuitive way to do that, especially if we want JSON to be the data-franca of our code chunks.

```JSON
    []
```

## Ticket_Validator

But something like this would be fine.

```Javascript
    function(ticket) {
        if (typeof ticket.name != "string") { return false; }
        if (typeof ticket.tickets_bought != "number") { return false; }
        return true;
    }
```

## Acquiring the Tickets => The Tickets

Allow exception: bash
```bash
jq .
```

We could do something like jq . $1 > ${TheTickets}, but given that The Tickets is a variable, the => in the header may be a good way to handle assignment.
The assumption is JSON being passed through STDOUT. The natural way for languages to grab command-line arguments should all work with the arguments passed
to the Layer7 program.

## All Stop Rules

- Reject the whole batch up front if any single entry bought more than 100 tickets (anti-abuse rule) — this should be a hard stop, nothing further runs.
- If there are fewer than 2 unique entrants, skip the drawing entirely and report "not enough entrants" instead of picking a winner.

If a code block ever returns an error level / return code instead of a normal exit, that should propagate and get handled, or not, by the Layer7 wrapper.

Allow exception: perl
```perl
my $seen = {};
foreach my $ticket ( @$TheTickets ) {
    if ($ticket->{tickets_bought} > 100) {
        die "Anti-Abuse Rule triggered!";
    } elsif (! Ticket_Validator($ticket)) {
        # Ticket_Validator is injected as a normal callable subroutine
        die "Type-checking error! Invalid data."
    } else {
        $seen->{ $ticket->{name} } = 1;
    }
}
die "Not enough contestants!" if (scalar keys %$seen < 2);
```

Notice that we haven't used any orchestration yet. Program flows straight through as read by default.

## Chicken Dinner <= The Tickets

- Otherwise, weight each entry by ticket count and pick a winner at random.
- Otherwise, announce the winner and also report the total number of tickets in play.

Ugh. Math. This code block is from Gemini:

Allow exception: python
```python
import sys
import json
import random

# Python natively reads everything from the inbound pipe (STDIN)
input_data = sys.stdin.read()
tickets = json.loads(input_data)

# Calculate the total pool size
total_tickets = sum(t['tickets_bought'] for t in tickets)

# Build a weighted list for selection
pool = []
for t in tickets:
    pool.extend([t['name']] * t['tickets_bought'])

# Pick a random winner from the pool
winner = random.choice(pool)

# Announce the results to STDOUT
print(f"Winner: {winner}")
print(f"Total tickets in play: {total_tickets}")
```
