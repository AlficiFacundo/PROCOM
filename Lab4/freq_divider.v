module freq_divider #(
    parameter N_PHASES = 4
)(
    input  wire                          clk,
    input  wire                          i_rst_n,
    input  wire                          en_tx,
    output reg  [$clog2(N_PHASES)-1:0]   phase_cnt, // fase alineada con la muestra actual
    output wire                          valid
);
    reg [$clog2(N_PHASES)-1:0] cnt;

    // 'valid' se dispara cuando el contador interno esta en 0,
    // es decir, en el ciclo en que se carga un simbolo nuevo.
    assign valid = (cnt == 0);

    always @(posedge clk or negedge i_rst_n) begin
        if (!i_rst_n) begin
            cnt       <= 0;
            phase_cnt <= N_PHASES-1;
        end else begin
            // phase_cnt se registra ANTES de incrementar 'cnt': asi, en el
            // mismo ciclo en que rc_tx carga el simbolo nuevo (cnt==0),
            // phase_sel sigue mostrando la fase 0 correspondiente a esa
            // carga, en vez del valor ya incrementado.
            phase_cnt <= cnt;
            if (en_tx)
                cnt <= (cnt == N_PHASES-1) ? 0 : cnt + 1'b1;
        end
    end
endmodule