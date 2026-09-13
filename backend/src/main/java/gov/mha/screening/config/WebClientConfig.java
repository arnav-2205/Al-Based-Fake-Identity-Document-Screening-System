package gov.mha.screening.config;

import io.netty.channel.ChannelOption;
import io.netty.handler.timeout.ReadTimeoutHandler;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

import java.util.concurrent.TimeUnit;

@Configuration
@RequiredArgsConstructor
public class WebClientConfig {

    private final AppProperties props;

    @Bean
    public WebClient aiWebClient() {
        int timeout = (int) props.ai().timeoutMs();
        HttpClient httpClient = HttpClient.create()
                .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, timeout)
                .doOnConnected(c -> c.addHandlerLast(
                        new ReadTimeoutHandler(timeout, TimeUnit.MILLISECONDS)));
        return WebClient.builder()
                .baseUrl(props.ai().baseUrl())
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .codecs(cfg -> cfg.defaultCodecs().maxInMemorySize(16 * 1024 * 1024))
                .build();
    }
}
