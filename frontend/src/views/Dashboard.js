import TextField from "@mui/material/TextField";
import Autocomplete from "@mui/material/Autocomplete";
import { Container } from "@mui/material";
import Button from "@mui/material/Button";

import { useState } from "react";

export default function Dashboard() {
  const [num, setNum] = useState(0);

  return (
    <Container sx={{}}>
      <Button
        onClick={() => {
          setNum(num + 1);
          console.log(num);
        }}
      >
        Press me!
      </Button>
    </Container>
  );
}
